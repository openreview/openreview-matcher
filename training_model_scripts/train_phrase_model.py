""" Train a phrase model on a corpus of document to automatically
detect common phrases """

from gensim.models import Phrases
import pickle
import argparse


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

def train_phrase_model(training_data_location, output_folder):
	""" Train phrase model (bigrams and trigrams) on training data """

	training_data = collect_training_data(training_data_location)
	
	print "Number of training documents: ", len(training_data)

	print "Training bigram model..."
	bigram_model = Phrases(training_data, min_count=5)

	print "Training trigram model..."
	trigram_model = Phrases(bigram_model[training_data], min_count=5)

	save_phrase_model(bigram_model, "bigram_model", output_folder)
	save_phrase_model(trigram_model, "trigram_model", output_folder)

def save_phrase_model(model, name, location):
	""" Save the phrase model to specified location """

	print "Saving {0} at {1}".format(name, location)

	with open("{0}/{1}.pkl".format(location, name), "w") as f:
		pickle.dump(model, f)


if __name__ == "__main__":

	# Example:
	# python2 train_phrase_model.py --data ../training_model_data/training_data.pkl --output ../trained_models/phrase

    parser = argparse.ArgumentParser()
    parser.add_argument('-d', '--data', help="location of training data (.pkl file)", required=True) 
    parser.add_argument('-o', '--output', help="folder to save phrase models")

    args = parser.parse_args()
    training_data_location = args.data 
    output_folder = args.output

    print "Training data location: ", training_data_location
    print "Output folder location: ", output_folder

    train_phrase_model(training_data_location, output_folder)

