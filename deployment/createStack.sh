docker swarm init --advertise-addr $(ifconfig enp0s3 | sed -En 's/127.0.0.1//;s/.*inet (addr:)?(([0-9]*\.){3}[0-9]*).*/\2/p')
#docker-swarm join --token <the token returned by the previous command> <the IP advertised previously>:2377
docker node update \
        --label-add web-service=true \
        --label-add nginx-service=true \
        --label-add mongo-service=true \
        --label-add postgres-service=true \
        --label-add backup-service=true \
	$HOSTNAME


#create volume
docker volume create -d local-persist -o mountpoint=/home/osboxes/copo/web-data --name=web-data
docker volume create -d local-persist -o mountpoint=/home/osboxes/copo/static-data --name=static-data
docker volume create -d local-persist -o mountpoint=/home/osboxes/copo/submission-data --name=submission-data
docker volume create -d local-persist -o mountpoint=/home/osboxes/copo/logs-data --name=logs-data
docker volume create -d local-persist -o mountpoint=/home/osboxes/copo/mongo-data --name=mongo-backup
docker volume create -d local-persist -o mountpoint=/home/osboxes/copo/postgres-data --name=postgres-backup

docker volume create mongo-data
docker volume create postgres-data

#create network
docker network create -d overlay copo-frontend-network
docker network create -d overlay copo-backend-network

#create secrets

docker secret create copo_mongo_initdb_root_password copo_mongo_initdb_root_password
docker secret create copo_mongo_user_password copo_mongo_user_password
docker secret create copo_postgres_user_password copo_postgres_user_password
docker secret create copo_web_secret_key copo_web_secret_key
docker secret create copo_orcid_secret_key copo_orcid_secret_key
docker secret create copo_figshare_consumer_secret_key copo_figshare_consumer_secret_key
docker secret create copo_figshare_client_id_key copo_figshare_client_id_key
docker secret create copo_figshare_client_secret_key copo_figshare_client_secret_key
docker secret create copo_google_secret_key copo_google_secret_key
docker secret create copo_twitter_secret_key copo_twitter_secret_key
docker secret create copo_facebook_secret_key copo_facebook_secret_key
docker secret create copo_webin_user copo_webin_user
docker secret create copo_webin_user_password copo_webin_user_password
docker secret create copo-project.crt copo-project.crt
docker secret create copo-project.key copo-project.key
docker secret create copo_nih_api_key copo_nih_api_key
docker secret create copo_public_name_service_api_key copo_public_name_service_api_key
docker secret create copo_mail_password copo_mail_password
docker secret create copo_bioimage_path copo_bioimage_path
docker secret create ecs_secret_key ecs_secret_key

docker stack deploy --compose-file demo.compose.yaml copo
