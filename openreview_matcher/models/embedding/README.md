## Implementation of an Embedding Model (skipgram w2v)

The Embedding Model is using a word2vec model trained on 1000s of scientific papers to generate word embeddings.
The model uses these word embeddings to generate scores between reviewers and papers.

In the Embedding Model we can represent a document as a average vector of word embeddings
Thus once we have this averaged word vector, we can then use a dot product based method such 
as cosine similarity to generate a score between 0-1 which expresses the similarity of two documents

Another way to represent documents is just represent them as a bag of words and them computing
the word movers distance between the distribution of word vectors of one document to the distribution 
of word vectors to another document. The word mover's distance is the minimum travel distance needed to move 
the word embeddings of one document to the word embeddings of another document








