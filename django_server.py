import os
import sys
import random
import requests
import json
from django.conf import settings
from django.core.management import execute_from_command_line
from django.http import JsonResponse, HttpResponse
from django.urls import path
from django.views.decorators.csrf import csrf_exempt

if not settings.configured:
    settings.configure(
        DEBUG=True,
        SECRET_KEY='secret_key_for_testing',
        ROOT_URLCONF=__name__,
        ALLOWED_HOSTS=['*'],
    )

CLICKHOUSE_URL = os.environ.get('CLICKHOUSE_URL', 'http://localhost:8123')
CLICKHOUSE_USER = os.environ.get('CLICKHOUSE_USER', 'default')
CLICKHOUSE_PASSWORD = os.environ.get('CLICKHOUSE_PASSWORD', '')

def get_mock_data(page, limit):
    offset = (page - 1) * limit
    categories = ['GAME', 'FAMILY', 'TOOLS', 'BUSINESS', 'LIFESTYLE']
    data = []
    for i in range(limit):
        idx = offset + i
        data.append({
            'App': f'Mock App {idx + 1}',
            'Category': categories[idx % len(categories)],
            'Rating': round(random.uniform(1.0, 5.0), 1),
            'Reviews': random.randint(0, 10000),
            'Size': f'{random.randint(10, 100)}M',
            'Installs': f'{random.randint(100, 1000)}+',
            'Type': 'Free',
            'Price': '0'
        })
    return data

# 3. View Function
@csrf_exempt
def milliondata(request):
    # Handle CORS manually
    if request.method == 'OPTIONS':
        response = HttpResponse()
        response["Access-Control-Allow-Origin"] = "*"
        response["Access-Control-Allow-Methods"] = "GET, OPTIONS"
        response["Access-Control-Allow-Headers"] = "*"
        return response

    try:
        page = int(request.GET.get('page', 1))
        limit = int(request.GET.get('limit', 20))
    except ValueError:
        return JsonResponse({'error': 'invalid page or limit'}, status=400)

    offset = (page - 1) * limit
    
    # Try connecting to ClickHouse
    query = f"SELECT App, Category, Rating, Reviews, Size, Installs, Type, Price FROM sample.milliondata LIMIT {limit} OFFSET {offset} FORMAT JSON"
    
    try:
        # print(f"Querying ClickHouse: {CLICKHOUSE_URL}")
        auth = None
        if CLICKHOUSE_USER:
            auth = (CLICKHOUSE_USER, CLICKHOUSE_PASSWORD)
            
        res = requests.post(
            f"{CLICKHOUSE_URL}/?query={query}", 
            auth=auth,
            timeout=5
        )
        
        if res.status_code == 200:
            ch_data = res.json()
            data = ch_data.get('data', [])
            response = JsonResponse(data, safe=False)
        else:
            raise Exception(f"ClickHouse status {res.status_code}")
            
    except Exception as e:
        print(f"ClickHouse error: {e}")
        print("Falling back to mock data")
        data = get_mock_data(page, limit)
        response = JsonResponse(data, safe=False)

    # Add CORS headers
    response["Access-Control-Allow-Origin"] = "*"
    return response

# 4. URL Configuration
urlpatterns = [
    path('milliondata', milliondata),
]

# 5. Run Server
if __name__ == "__main__":
    # Default to port 5000 to match previous setup
    from django.core.management.commands.runserver import Command as RunserverCommand
    
    # If no args provided, inject runserver and port
    if len(sys.argv) == 1:
        sys.argv.append("runserver")
        sys.argv.append("5000")
    elif len(sys.argv) == 2 and sys.argv[1] == 'runserver':
         sys.argv.append("5000")
        
    execute_from_command_line(sys.argv)
