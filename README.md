Dependencies:
python3.4
django
biopython (requires numpy)
django-registration-redux
pymongo (for bson module)
beautifulsoup4 (for google scholar)


http://stackoverflow.com/questions/20175243/django-gunicorn-not-load-static-files
create error http

in nginx config file
error_page   500 502 503 504  /50x.html;
location = /50x.html {
    root   html;
}
