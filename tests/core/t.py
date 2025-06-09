import uuid
import requests
import json


def test():
    url = "https://www.printemps.com/ajax.php"
    
    boundary = f"----Boundary{uuid.uuid4().hex}"

    headers = {
        "Accept": "application/json",
        "Content-Type": f"multipart/form-data; boundary={boundary}",
        "X-Requested-With": "XMLHttpRequest",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36 Edg/135.0.0.0",
        "Referer": "https://www.printemps.com/fr/fr/parfum",
        
    }
    data = {
        "do": "search",
        "action": "search",
        "currentUrl": "https://www.printemps.com/fr/fr/parfum/page/2",
        "requests": [
            {
                "indexName": "parfum",
                "params": {
                    "hitsPerPage": "60",
                    "clickAnalytics]": "true",
                    "query]": "",
                    "highlightPreTag": "__ais-highlight__",
                    "highlightPostTag": "__/ais-highlight__",
                    "page": "1",
                    "maxValuesPerFacet": "400",
                    "facets": [
                        "mark",
                        "categoryMenus",
                        "categoryDetails",
                        "color",
                        "soldes",
                        "attributes.Aspect",
                        "attributes.Coupe",
                        "attributes.Détails",
                        "attributes.Longueur",
                        "attributes.Notes olfactives",
                        "merchants",
                        "prices",
                    ],
                    "tagFilters]": "",
                },
            }
        ],
    }

    data2 = {
        "do": "search",
        "action": "search",
        "currentUrl": "https://www.printemps.com/fr/fr/parfum/page/2",
        "requests[0][indexName]": "parfum",
        "requests[0][params][hitsPerPage]": "60",
        "requests[0][params][clickAnalytics]": "true",
        "requests[0][params][query]": "",
        "requests[0][params][highlightPreTag]": "__ais-highlight__",
        "requests[0][params][highlightPostTag]": "__/ais-highlight__",
        "requests[0][params][page]": "1",
        "requests[0][params][maxValuesPerFacet]": "400",
        "requests[0][params][facets][0]": "mark",
        "requests[0][params][facets][1]": "categoryMenus",
        "requests[0][params][facets][2]": "categoryDetails",
        "requests[0][params][facets][3]": "color",
        "requests[0][params][facets][4]": "soldes",
        "requests[0][params][facets][5]": "attributes.Aspect",
        "requests[0][params][facets][6]": "attributes.Coupe",
        "requests[0][params][facets][7]": "attributes.Détails",
        "requests[0][params][facets][8]": "attributes.Longueur",
        "requests[0][params][facets][9]": "attributes.Notes olfactives",
        "requests[0][params][facets][10]": "merchants",
        "requests[0][params][facets][11]": "prices",
        "requests[0][params][tagFilters]": "",
    }
    
    data3 = f"""--{boundary}
Content-Disposition: form-data; name="do"

search
--{boundary}
Content-Disposition: form-data; name="action"

search
--{boundary}
Content-Disposition: form-data; name="currentUrl"

https://www.printemps.com/fr/fr/parfum/page/2
--{boundary}
Content-Disposition: form-data; name="requests[0][indexName]"

parfum
--{boundary}
Content-Disposition: form-data; name="requests[0][params][hitsPerPage]"

60
--{boundary}
Content-Disposition: form-data; name="requests[0][params][clickAnalytics]"

true
--{boundary}
Content-Disposition: form-data; name="requests[0][params][query]"


--{boundary}
Content-Disposition: form-data; name="requests[0][params][highlightPreTag]"

__ais-highlight__
--{boundary}
Content-Disposition: form-data; name="requests[0][params][highlightPostTag]"

__/ais-highlight__
--{boundary}
Content-Disposition: form-data; name="requests[0][params][page]"

1
--{boundary}
Content-Disposition: form-data; name="requests[0][params][maxValuesPerFacet]"

400
--{boundary}
Content-Disposition: form-data; name="requests[0][params][facets][0]"

mark
--{boundary}
Content-Disposition: form-data; name="requests[0][params][facets][1]"

categoryMenus
--{boundary}
Content-Disposition: form-data; name="requests[0][params][facets][2]"

categoryDetails
--{boundary}
Content-Disposition: form-data; name="requests[0][params][facets][3]"

color
--{boundary}
Content-Disposition: form-data; name="requests[0][params][facets][4]"

soldes
--{boundary}
Content-Disposition: form-data; name="requests[0][params][facets][5]"

attributes.Aspect
--{boundary}
Content-Disposition: form-data; name="requests[0][params][facets][6]"

attributes.Coupe
--{boundary}
Content-Disposition: form-data; name="requests[0][params][facets][7]"

attributes.Détails
--{boundary}
Content-Disposition: form-data; name="requests[0][params][facets][8]"

attributes.Longueur
--{boundary}
Content-Disposition: form-data; name="requests[0][params][facets][9]"

attributes.Notes olfactives
--{boundary}
Content-Disposition: form-data; name="requests[0][params][facets][10]"

merchants
--{boundary}
Content-Disposition: form-data; name="requests[0][params][facets][11]"

prices
--{boundary}
Content-Disposition: form-data; name="requests[0][params][tagFilters]"


--{boundary}--"""
    response = requests.post(url, data=data3, headers=headers, timeout=10)
    return response


t = test()
print(t)
print(t.text)
print(t.json())
