```
cd backend
uvicorn index:app --reload
```

mysql docker

```
docker run --name mysqldb --platform linux/x86_64 -e MYSQL_DATABASE=admin -e MYSQL_ROOT_PASSWORD=admin -p 3306:3306 mysql:latest
```

API Server
```
http://localhost:8000/docs
```
