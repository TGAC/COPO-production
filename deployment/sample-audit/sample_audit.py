import pymongo
import pymongo.errors as pymongo_errors
import urllib.parse
import os

def get_env(env_key):
    env_value = str()
    if env_key in os.environ:
        env_value = os.getenv(env_key)

    # resolve for file assignment
    file_env = os.environ.get(env_key + "_FILE", str())
    if len(file_env) > 0:
        try:
            with open(file_env, 'r') as mysecret:
                data = mysecret.read().replace('\n', '')
                env_value = data
        except:
            pass
    return env_value

username = urllib.parse.quote_plus(get_env("MONGO_USER"))
password = urllib.parse.quote_plus(get_env("MONGO_USER_PASSWORD"))
mongo = urllib.parse.quote_plus(get_env("MONGO_HOST"))
port = urllib.parse.quote_plus(get_env("MONGO_PORT"))
myclient = pymongo.MongoClient(f"mongodb://{username}:{password}@{mongo}:{port}/")
mydb = myclient["copo_mongo"]

def process_changes(doc):
    print(doc)
    mydb["AuditCollection"].insert_one({"doc_id":doc["documentKey"]["_id"], "doc_type": doc["ns"]["coll"], "action": doc["operationType"], "updatedFields": doc["updateDescription"].get("updatedFields",[]), "removedFields": doc["updateDescription"].get("removedFields",[]), "datetime":doc["clusterTime"]})


try:
    resume_token = None
    pipeline = [{'$match': {'operationType': 'update'}}]
    with mydb.SampleCollection.watch(pipeline=pipeline, 
        full_document_before_change="whenAvailable"
        ) as stream:
        for update_change in stream:
            process_changes(update_change)
            resume_token = stream.resume_token
except pymongo.errors.PyMongoError:
    # The ChangeStream encountered an unrecoverable error or the
    # resume attempt failed to recreate the cursor.
    if resume_token is None:
        # There is no usable resume token because there was a
        # failure during ChangeStream initialization.
        print.error('...')
    else:
        # Use the interrupted ChangeStream's resume token to create
        # a new ChangeStream. The new stream will continue from the
        # last seen insert change without missing any events.
        with mydb.SampleCollection.watch(pipeline=pipeline, 
                full_document_before_change="whenAvailable",
                resume_after=resume_token) as stream:
            for update_change in stream:
                process_changes(update_change)
