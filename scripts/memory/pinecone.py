
import pinecone

from memory.base import MemoryProviderSingleton, get_ada_embedding


class PineconeMemory(MemoryProviderSingleton):
    def __init__(self, cfg):
        pinecone_api_key = cfg.pinecone_api_key
        pinecone_region = cfg.pinecone_region
        pinecone.init(api_key=pinecone_api_key, environment=pinecone_region)
        dimension = 1536
        metric = "cosine"
        pod_type = "p1"
        table_name = "research"
        # this assumes we don't start with memory.
        # for now this works.
        # we'll need a more complicated and robust system if we want to start with memory.
        self.vec_num = 0
        if table_name not in pinecone.list_indexes():
            pinecone.create_index(table_name, dimension=dimension, metric=metric, pod_type=pod_type)
        self.index = pinecone.Index(table_name)

    def add(self, data):
        vector = get_ada_embedding(data)
        # no metadata here. We may wish to change that long term.
        resp = self.index.upsert([(str(self.vec_num), vector, {"raw_text": data})])
        _text = f"Inserting data into memory at index: {self.vec_num}:\n data: {data}"
        self.vec_num += 1
        return _text

    def get(self, data):
        return self.get_relevant(data, 1)

    def clear(self):
        self.index.delete(deleteAll=True)
        return "Obliviated"

    def get_relevant(self, data, num_relevant=5, similarity_threshold=0.9):
        """
        Returns all the data in the memory that is relevant to the given data.
        :param data: The data to compare to.
        :param num_relevant: The number of relevant data to return. Defaults to 3
        :param similarity_threshold: The similarity threshold to filter results. Defaults to 0.9
        """
        query_embedding = get_ada_embedding(data)
        results = self.index.query(query_embedding, top_k=num_relevant, include_metadata=True)
        # Filter the results based on the similarity threshold
        filtered_results = [item for item in results.matches if item.score >= similarity_threshold]
        # Sort the filtered results by score
        sorted_results = sorted(filtered_results, key=lambda x: x.score, reverse=True)
        return [str(item['metadata']["raw_text"]) for item in sorted_results]

    def get_stats(self):
        return self.index.describe_index_stats()
