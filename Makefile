build:
	if [ ! -d "./data" ]; then  mkdir -p data/elasticsearch && mkdir -p data/web && mkdir -p data/nginx && mkdir -p data/mysql && mkdir -p  data/redis && echo "create volumes directorys ok ."; fi
	docker-compose up
	# docker-compose up --build -d

clean:
	docker-compose down
	docker system prune -fa
