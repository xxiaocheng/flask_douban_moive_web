build:
	# docker-compose up --build -d
	if [ ! -d "./data" ]; then mkdir -p data/mongodb && mkdir -p data/nginx && mkdir -p  data/redis && echo "create volumes directorys ok ."; fi
	docker-compose up 

clean:
	docker-compose down
	docker system prune -fa
