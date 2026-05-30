import sys
import json
import re
import fitz  
def extract_github_profile(file_path):
    """Extract GitHub profile URL from PDF using PyMuPDF"""
    try:
        links = []
        doc = fitz.open(file_path)
        for page in doc:
            for link in page.get_links():
                if "uri" in link:
                    links.append(link["uri"])
        text = ""
        for page in doc:
            text += page.get_text()
        
        url_pattern = r"(https?://[^\s]+)"
        text_urls = re.findall(url_pattern, text)
        links.extend(text_urls)
        github_links = [l for l in links if "github.com" in l.lower()]
        github_profiles = []
        for link in github_links:
            # Match profile URLs like https://github.com/username
            match = re.match(r"https?://(?:www\.)?github\.com/([a-zA-Z0-9-_]+)/?$", link.strip("/"))
            if match:
                username = match.group(1)
                # Skip common non-profile patterns
                excluded = ['login', 'signup', 'join', 'pricing', 'features', 'about', 
                           'contact', 'blog', 'topics', 'trending', 'explore', 'marketplace', 
                           'sponsors', 'modesty', 'in']
                if username.lower() not in excluded:
                    github_profiles.append(username)
        
        # If no clean profile found, try extracting from any GitHub URL
        if not github_profiles:
            for link in github_links:
                match = re.search(r"github\.com/([a-zA-Z0-9-_]+)", link)
                if match:
                    username = match.group(1)
                    excluded = ['login', 'signup', 'join', 'pricing', 'features', 'about', 
                               'contact', 'blog', 'topics', 'trending', 'explore', 'marketplace', 
                               'sponsors', 'modesty', 'in']
                    if username.lower() not in excluded:
                        github_profiles.append(username)
        
        # Return the first valid profile
        if github_profiles:
            
            github_profiles.sort(key=lambda x: len(x), reverse=True)
            return {"success": True, "username": github_profiles[0], "allLinks": github_links}
        
        return {"success": False, "error": "No GitHub profile found", "allLinks": github_links}
        
    except Exception as e:
        return {"success": False, "error": str(e)}

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(json.dumps({"success": False, "error": "No file path provided"}))
        sys.exit(1)
    
    file_path = sys.argv[1]
    result = extract_github_profile(file_path)
    print(json.dumps(result))
