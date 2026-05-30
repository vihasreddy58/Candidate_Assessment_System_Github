import React, { useMemo, useState } from 'react';
import { useTable, useSortBy, usePagination, useGlobalFilter } from 'react-table';
import { ArrowLeft, Eye, Download, Filter, Search, ChevronLeft, ChevronRight } from 'lucide-react';
import './Dashboard.css';

const formatScore = (value) => {
  if (value === null || value === undefined) return 'N/A';
  const number = Number(value);
  if (Number.isNaN(number)) return 'N/A';
  return Number.isInteger(number) ? String(number) : number.toFixed(1);
};

const getGithubUrl = (row) => {
  if (row?.githubUrl) return row.githubUrl;
  if (row?.githubUsername) return `https://github.com/${row.githubUsername}`;
  return '';
};

const BulkDashboard = ({ summary, failures = [], onSelectReport, onReset }) => {
  const [ratingFilter, setRatingFilter] = useState('all');
  const [searchText, setSearchText] = useState('');
  const rows = summary?.rows || [];
  const aggregates = summary?.aggregates || {};

  const filteredRows = useMemo(() => {
    const normalizedSearch = searchText.trim().toLowerCase();

    return rows.filter((r) => {
      const matchesRating = ratingFilter === 'all' || (r.rating || '').toLowerCase() === ratingFilter;
      if (!matchesRating) return false;

      if (!normalizedSearch) return true;

      const searchable = [
        r.name,
        r.githubUsername,
        r.rating,
        r.codeQualityGrade,
        String(r.overallScore ?? ''),
        String(r.skillMatchPercentage ?? ''),
        String(r.codeHealthScore ?? '')
      ]
        .filter(Boolean)
        .join(' ')
        .toLowerCase();

      return searchable.includes(normalizedSearch);
    });
  }, [rows, ratingFilter, searchText]);

  const columns = useMemo(() => [
    { Header: 'Name', accessor: 'name' },
    {
      Header: 'GitHub',
      accessor: 'githubUsername',
      Cell: ({ value, row }) => {
        const githubUrl = getGithubUrl(row.original);
        if (!value || !githubUrl) return 'N/A';

        return (
          <a
            className="github-link"
            href={githubUrl}
            target="_blank"
            rel="noopener noreferrer"
            title="Open GitHub profile"
            onClick={(event) => event.stopPropagation()}
          >
            @{value}
          </a>
        );
      }
    },
    { Header: 'Overall', accessor: 'overallScore', Cell: ({ value }) => <span className="pill subtle">{value ?? 0}</span> },
    { Header: 'Rating', accessor: 'rating', Cell: ({ value }) => <span className={`pill rating-${(value || 'na').toLowerCase().replace(/\s+/g, '-')}`}>{value || 'N/A'}</span> },
    { Header: 'Skill Auth', accessor: 'skillAuthenticity' },
    { Header: 'Repo Quality', accessor: 'codeQualityScore', Cell: ({ row }) => `${row.original.codeQualityScore} (${row.original.codeQualityGrade})` },
    // { Header: 'Code Health', accessor: 'codeHealthScore', Cell: ({ value }) => <span className="pill subtle">{formatScore(value)}</span> },
    { Header: 'Commit Activity', accessor: 'commitActivityScore' },
    { Header: 'Tech Stack', accessor: 'techStackScore' },
    { Header: 'Profile', accessor: 'profileSignalScore' },
    { Header: 'Skill Match %', accessor: 'skillMatchPercentage' },
    {
      Header: '',
      id: 'actions',
      disableSortBy: true,
      Cell: ({ row }) => (
        <button
          className="btn-pill"
          onClick={(event) => {
            event.stopPropagation();
            onSelectReport(row.original.id ?? (row.index + 1));
          }}
        >
          <Eye size={16} /> View
        </button>
      )
    }
  ], [onSelectReport]);

  const hasActiveFilters = ratingFilter !== 'all' || Boolean(searchText.trim());

  const clearFilters = () => {
    setRatingFilter('all');
    setSearchText('');
    gotoPage(0);
  };

  const tableInstance = useTable({
    columns,
    data: filteredRows,
    initialState: {
      sortBy: [{ id: 'overallScore', desc: true }],
      pageSize: 10,
      pageIndex: 0
    }
  }, useGlobalFilter, useSortBy, usePagination);

  const {
    getTableProps,
    getTableBodyProps,
    headerGroups,
    prepareRow,
    page,
    canPreviousPage,
    canNextPage,
    pageOptions,
    pageCount,
    gotoPage,
    nextPage,
    previousPage,
    setPageSize,
    state: { pageIndex, pageSize }
  } = tableInstance;

  const exportCsv = () => {
    const headers = ['Name','GitHub','GitHub URL','Overall Score','Rating','Skill Authenticity','Code Quality Score','Code Quality Grade','Code Health Score','Commit Activity','Tech Stack','Profile Signal','Skill Match %'];
    const escapeCsv = (value) => {
      const raw = value ?? '';
      const safe = String(raw).replace(/"/g, '""');
      return /[",\n]/.test(safe) ? `"${safe}"` : safe;
    };

    const lines = filteredRows.map(r => {
      const githubUrl = getGithubUrl(r);
      const githubText = r.githubUsername ? `@${r.githubUsername}` : '';
      const githubHyperlink = (githubUrl && githubText)
        ? `=HYPERLINK("${githubUrl}","${githubText}")`
        : githubText;

      return [
      r.name || 'N/A',
      githubHyperlink,
      githubUrl,
      r.overallScore,
      r.rating,
      r.skillAuthenticity,
      r.codeQualityScore,
      r.codeQualityGrade,
      formatScore(r.codeHealthScore),
      r.commitActivityScore,
      r.techStackScore,
      r.profileSignalScore,
      r.skillMatchPercentage
    ].map(escapeCsv).join(',');
    });
    const bom = '\uFEFF';
    const csv = [headers.join(','), ...lines].join('\n');
    const blob = new Blob([bom + csv], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = 'analysis-summary.csv';
    link.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="dashboard">
      <div className="dashboard-header">
        <div className="header-left">
          <h1>Analysis Results</h1>
          <p>{summary?.processed || 0} processed · {summary?.failed || 0} failed · {filteredRows.length} shown</p>
        </div>
        <div className="header-actions">
          <button className="btn-secondary btn-secondary-solid" onClick={exportCsv}>
            <Download size={16} /> Export CSV
          </button>
          <button className="btn-secondary btn-secondary-solid" onClick={onReset}>
            <ArrowLeft size={16} /> Back to Upload
          </button>
        </div>
      </div>

      
      <div className="section-card">
        <h3>Candidates</h3>
        <div className="table-controls">
          <div className="control-group search-control-group">
            <Search size={14} />
            <input
              type="text"
              placeholder="Search by name, username, rating..."
              value={searchText}
              onChange={(e) => setSearchText(e.target.value)}
            />
          </div>
          <div className="control-group">
            <Filter size={14} />
            <select value={ratingFilter} onChange={(e) => setRatingFilter(e.target.value)}>
              <option value="all">All ratings</option>
              <option value="excellent">Excellent</option>
              <option value="very good">Very Good</option>
              <option value="good">Good</option>
              <option value="average">Average</option>
              <option value="below average">Below Average</option>
            </select>
          </div>
          {hasActiveFilters && (
            <button className="btn-secondary compact" onClick={clearFilters}>
              Clear Filters
            </button>
          )}
          <div className="control-group">
            <label htmlFor="bulk-page-size">Rows</label>
            <select
              id="bulk-page-size"
              value={pageSize}
              onChange={(e) => setPageSize(Number(e.target.value))}
            >
              {[10, 20, 50].map(size => (
                <option key={size} value={size}>{size}</option>
              ))}
            </select>
          </div>
          <small>Click column headers to sort</small>
        </div>

        {hasActiveFilters && (
          <div className="active-filters">
            {ratingFilter !== 'all' && <span className="filter-chip">Rating: {ratingFilter}</span>}
            {Boolean(searchText.trim()) && <span className="filter-chip">Search: {searchText.trim()}</span>}
          </div>
        )}

        <div className="responsive-table sticky-head">
          <table {...getTableProps()}>
            <thead>
              {headerGroups.map(headerGroup => (
                <tr {...headerGroup.getHeaderGroupProps()}>
                  {headerGroup.headers.map(column => (
                    <th {...column.getHeaderProps(column.getSortByToggleProps())}>
                      {column.render('Header')}
                      {column.isSorted ? (column.isSortedDesc ? ' ↓' : ' ↑') : ''}
                    </th>
                  ))}
                </tr>
              ))}
            </thead>
            <tbody {...getTableBodyProps()}>
              {page.map(row => {
                prepareRow(row);
                const reportId = row.original.id ?? (row.index + 1);
                return (
                  <tr
                    {...row.getRowProps()}
                    className="candidate-row"
                    role="button"
                    tabIndex={0}
                    onClick={() => onSelectReport(reportId)}
                    onKeyDown={(event) => {
                      if (event.key === 'Enter' || event.key === ' ') {
                        event.preventDefault();
                        onSelectReport(reportId);
                      }
                    }}
                  >
                    {row.cells.map(cell => (
                      <td {...cell.getCellProps()}>{cell.render('Cell')}</td>
                    ))}
                  </tr>
                );
              })}
              {page.length === 0 && (
                <tr>
                  <td colSpan={columns.length} className="table-empty-state">
                    No candidates match the current filters. Try changing rating or search text.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

        <div className="pagination-bar">
          <div className="pagination-summary">
            Page {pageIndex + 1} of {pageCount || 1}
          </div>
          <div className="pagination-actions">
            <button className="btn-secondary compact" onClick={() => gotoPage(0)} disabled={!canPreviousPage}>
              First
            </button>
            <button className="btn-secondary compact" onClick={previousPage} disabled={!canPreviousPage}>
              <ChevronLeft size={14} /> Prev
            </button>
            <button className="btn-secondary compact" onClick={nextPage} disabled={!canNextPage}>
              Next <ChevronRight size={14} />
            </button>
            <button className="btn-secondary compact" onClick={() => gotoPage(pageCount - 1)} disabled={!canNextPage}>
              Last
            </button>
          </div>
          <div className="pagination-jump">
            <label htmlFor="bulk-page-jump">Go to</label>
            <input
              id="bulk-page-jump"
              type="number"
              min={1}
              max={pageOptions.length || 1}
              value={pageIndex + 1}
              onChange={(e) => {
                const next = e.target.value ? Number(e.target.value) - 1 : 0;
                gotoPage(Number.isNaN(next) ? 0 : next);
              }}
            />
          </div>
        </div>
      </div>

      {failures?.length > 0 && (
        <div className="section-card">
          <h3>Failed Files</h3>
          <ul className="failures-list">
            {failures.map((f, idx) => (
              <li key={idx}>{f.filename || 'Unknown file'} — {f.error || 'Unexpected error'}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
};

export default BulkDashboard;
