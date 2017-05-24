import itertools
import string
import nltk

def extract_candidate_chunks(text, grammar=r'NP: {<JJ>*<NN>}', delimiter='_', stemmer=None):

    # exclude candidates that are stop words or entirely punctuation
    punct = set(string.punctuation)
    stop_words = set(nltk.corpus.stopwords.words('english'))

    # tokenize, POS-tag, and chunk using regular expressions
    chunker = nltk.chunk.regexp.RegexpParser(grammar)
    tagged_sents = nltk.pos_tag_sents(nltk.word_tokenize(sent) for sent in nltk.sent_tokenize(text))

    all_chunks = list(itertools.chain.from_iterable(
        nltk.chunk.tree2conlltags(chunker.parse(tagged_sent)) for tagged_sent in tagged_sents)
    )

    # join constituent chunk words into a single chunked phrase

    if stemmer != None:

        candidates = []
        for key, group in itertools.groupby(all_chunks, lambda (word,pos,chunk): chunk != 'O'):
            if key:
                words = []
                for word, pos, chunk in group:
                    try:
                        word = stemmer.stem(word)
                    except IndexError:
                        print "word unstemmable:",word
                    words.append(word)
                candidates.append(delimiter.join(words).lower())

    else:
        candidates = [delimiter.join(word for word, pos, chunk in group).lower()
                      for key, group in itertools.groupby(all_chunks, lambda (word,pos,chunk): chunk != 'O') if key]


    return [cand for cand in candidates
            if cand not in stop_words and not all(char in punct for char in cand)]


def extract_candidate_words(text, good_tags=set(['JJ','JJR','JJS','NN','NNP','NNS','NNPS']), stemmer=None):
    # exclude candidates that are stop words or entirely punctuation
    punct = set(string.punctuation)
    stop_words = set(nltk.corpus.stopwords.words('english'))

    # tokenize and POS-tag words
    tagged_words = itertools.chain.from_iterable(nltk.pos_tag_sents(nltk.word_tokenize(sent)
                                                                    for sent in nltk.sent_tokenize(text)))
    # filter on certain POS tags and lowercase all words

    if stemmer!=None:
        candidates = [stemmer.stem(word.lower()) for word, tag in tagged_words
                      if tag in good_tags and word.lower() not in stop_words
                      and not all(char in punct for char in word)]
    else:
        candidates = [word.lower() for word, tag in tagged_words
                      if tag in good_tags and word.lower() not in stop_words
                      and not all(char in punct for char in word)]

    return candidates
