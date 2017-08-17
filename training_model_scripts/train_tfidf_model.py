# Script to train a tf-idf model on a corpus of document for a downstream task 
# such as getting keywords from a document

from sklearn.feature_extraction.text import TfidfVectorizer
import pickle
import argparse


def collect_training_data(training_data_location):
	""" 
	Gather all of the data needed to train the tf-idf model 
	
	NOTE: you can also train the phrase model on other documents. Just 
	make this method returns all of the documents you want to train on
	"""

	print "Getting training data from {0}".format(training_data_location)

	with open(training_data_location, "r") as f:
		training_data = pickle.load(f)

	return [doc.split() for docin training_data]

def get_phrase_models(phrase_model_location):

	print "Getting phrase models from {0}".format(phrase_model_location)

	with open(phrase_model_location + "bigram_model.bin") as f:
		bigram_model = pickle.load(f)

	with open(phrase_model_location + "trigram_model.bin") as g: 
		trigram_model = pickle.load(g)

	return bigram_model, trigram_model


def trigram_transformer(words, bigram_model, trigram_model):
	""" Transform a document into a document with phrases using the learned phrase model """
	bigrams = bigram_model[words]
	trigrams = trigram_model[bigrams]
	return trigrams

def apply_phrase_model_to_training_documents(training_documents, bigram_model, trigram_model):

	print "Apply phrase model to {0} documents...".format(len(training_documents))

	return [trigram_transformer(doc, bigram_model, trigram_model) for doc in training_documents] # returns a list of documents where each document is encoded as a list of tokens

def train_tfidf_model(training_documents, tfidf_settings, save_location):
    """ Train a tfidf model on a set of document """

    print "Training tfidf model on {0} documents".format(len(training_documents))

    tfidf = TfidfVectorizer(**tfidf_settings)

    print "Tfidf model: " tfidf

    tfidf.fit(training_documents)
    
    print "Done training..."
      
    save_model(tfidf, save_location)

def save_model(model, location):
	""" Save the tfidf model """

	print "Saving model to: ", location	
	model.save(location + "tfidfvectorizer.pkl")


if __name__ == "__main__:

	parser = argparse.ArgumentParser()
	parser.add_argument("-d", "--data", help="location of training data (.pkl) file", required=True)
	parser.add_argument("-p", "--phrases", help="location of phrase models")
	parser.add_argument("-s", "--save", help="location to save tfidf model")
	
	args = parser.parse_args()
	training_data_location = args.data	
	phrase_model_location = args.phrases
	save_location = args.save


	training_data = collect_training_data(training_data_location)

	bigram_model, trigram_model = get_phrase_models(phrase_model_location)	

	training_data_with_phrases = apply_phrase_model_to_training_documents(training_data, bigram_model, trigram_model)
    training_data_with_phrases = [" ".join(doc) for doc in training_data_with_phrases]

    train_tfidf_model(training_data_with_phrases, {"max_df": .80}, save_location)