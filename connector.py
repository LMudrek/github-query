from github import Github
import urllib.parse
import json 

# Authentication
g = Github("")

# Define the search query
query = 'angular'
encoded_query = urllib.parse.quote(query)

qualifiers = {
    "filename":"package.json",
    "repo": "gothinkster/angularjs-realworld-example-app"
}

# Perform the search
results = g.search_code(query=encoded_query, sort="indexed", order="asc", highlight=True, **qualifiers)

# Print out the results
for result in results:
    angular_js_version = json.loads(result.decoded_content)["dependencies"]["angular"]
    
    print(f"Repository: {result.repository.full_name}")
    print(f"File path: {result.path}")
    print(f"URL: {result.html_url}")
    print(f"Angular JS: {angular_js_version}")
