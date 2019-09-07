from django.db import models
from helper import common as commonHelper

class Searcher:
    def __init__(self, docs, vocab):
        self.docs = docs
        self.vocab = vocab

    def init_vector(self, terms):
        vector = [0] * len(self.vocab)
        for term in terms:
            try:
                 vector[self.vocab.index(term)] += 1
            except ValueError:
                print("can not response query: ", term)

       
        return vector

    def search(self, terms):
        res = {}
        qvector = self.init_vector(terms)
        # print([x for x in qvector if x != 0])
        for doc in self.docs:
            res[doc.id] = commonHelper.cosine(doc.get_vector(), qvector)

        doc_ids = sorted(res.items(), key=lambda kv: -kv[1])
        # print(doc_ids)
        return [doc[0] for doc in doc_ids if doc[1] > 0.0]

