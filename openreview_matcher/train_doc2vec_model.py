""" A script for training a doc2vec (paragraph vectors) model using gensim """
import pickle
import argparse 
from gensim.models import Doc2Vec 
from gensim.models.doc2vec import TaggedDocument

def collect_training_data(training_data_location):
	""" 
	Gather all of the data needed to train the phrase model 
	
	NOTE: you can also train the phrase model on other documents. Just 
	make this method returns all of the documents you want to train on
	"""

	print "Getting training data from {0}".format(training_data_location)

	with open(training_data_location, "r") as f:
		training_data = pickle.load(f)

	return [doc.split() for doc in training_data]

def get_phrase_models(phrase_model_location):

	print "Getting phrase models from {0}".format(phrase_model_location)

	with open(phrase_model_location + "bigram_model.bin") as f:
		bigram_model = pickle.load(f)
	with open(phrase_model_location + "trigram_model.bin") as g: 
		trigram_model = pickle.load(g)

	return bigram_model, trigram_model


def apply_phrase_model_to_training_documents(training_documents, bigram_model, trigram_model):

	print "Apply phrase model to {0} documents...".format(len(training_documents))

	def trigram_transformer(words):
    """ Transform a document into a document with phrases using the learned phrase model """

	    # words = tokenize(doc)
	    bigrams = bigram_model[words]
	    trigrams = trigram_model[bigrams]
	    return trigrams

	return [trigram_transformer(doc) for doc in training_documents] # returns a list of documents where each document is encoded as a list of tokens

def preprocess_uai_data(uai_data_location, bigram_model, trigram_model):

	with open(uai_data_location, "r") as f:
		uai_data = pickle.load(f)

	preprocessed_uai_data = {}

	for tag, papers in uai_data.iteritems()
		preprocessed_uai_data[tag] = apply_phrase_model_to_training_documents(papers, bigram_model, trigram_model)
	return preprocess_uai_data		

def create_tagged_documents(training_documents, uai_data):
	tagged_documents = []
	for tag, tokens in enumerate(training_documents, start=1):
		td = TaggedDocument(tokens, tags=[tag])
		tagged_documents.append(td)

	if len(uai_data) > 0:
		for tag, papers in uai_data.iteritems():
			for paper in papers:
				td = TaggedDocument(paper, tags=[tag])
				print "Tag Example:", td
				tagged_documents.append(td)

	return tagged_documents

def train_doc2vec_model(training_documents, doc2vec_settings, save_location):

	print "Number of docs for training: ", len(training_documents)

	print "Examle doc for training: ", training_documents[0]

	print "Starting to train doc2vec model..."
	model = Doc2Vec(training_documents, min_count=5, sample=1e-5, hs=0, dm=0, negative=5, dbow_words=1, **doc2vec_settings)
	print "Done training doc2vec model..."

	model.delete_temporary_training_data(keep_doctags_vectors=True, keep_inference=True)

	save_model(model, save_location)

def save_model(model, location):
	""" Save the doc2vec model """

	print "Saving model to: ", location	
	model.save(location + "doc2vec.bin")


if __name__ == "__main__":

	parser = argparse.ArgumentParser()
	parser.add_argument("-d", "--data", help="location of training data (.pkl) file", required=True)
	parser.add_argument("-p", "--phrases", help="location of phrase models")
	parser.add_argument("-em", "--size", help="size of the embedding", required=True)
	parser.add_argument("-i", "--iter", help="number of iterations", required=True)
	parser.add_argument("-w", "--window", help="window size", required=True)
	parser.add_argument("-wrk", "--workers", help="number of workers", required=True)
	parser.add_argument("-s", "--save", help="location to save word2vec model")
	parser.add_argument("-u", "--uai_data", help="use the uai data in addition to the training documents")

	args = parser.parse_args()
	training_data_location = args.data	

	phrase_model_location = args.phrases

	model_embedding_size = args.size
	model_iter = args.iter
	model_window = args.window
	model_workers = args.workers

	uai_data_location = args.uai_data
	save_location = args.save

	print args

	training_data = collect_training_data(training_data_location)

	bigram_model, trigram_model = get_phrase_models(phrase_model_location)	

	training_data_with_phrases = apply_phrase_model_to_training_documents(training_data, bigram_model, trigram_model)

	if uai_data is not None:
		uai_data_with_phrases = preprocess_uai_data(uai_data_location, bigram_model, trigram_model)
	else:
		uai_data_with_phrases = []

	tagged_documents = create_tagged_documents(training_data_with_phrases, uai_data_with_phrases)

	print "Number of tagged documents for training: ", len(tagged_documents)





