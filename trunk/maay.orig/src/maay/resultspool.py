"""
        A resultspool handles the response of one query.
"""

import resultspool

import globalvars
import tools
import constants

SCORE_SORTED = 0
DATE_SORTED = 1
RELEVANCE_SORTED = 2
POPULARITY_SORTED = 3

NO_RESULT_FILTER = 0
DOCUMENT_RESULT_FILTER = 1
MULTIMEDIA_RESULT_FILTER = 2
ARCHIVE__RESULT_FILTER = 3


#       def addResult(self, document_id, score, relevance, popularity, date):
# title, excerpt, url, size, date
class SearchEngineResult:
    def __init__(self, title, excerpt, url, size, date):
        self.title = title
        self.excerpt = excerpt
        self.url = url
        self.size = size
        self.date = date
        self.state = constants.KNOWN_STATE
        
    def __str__(self):
        print "maay.SearchEngineResult: title=%s, excerpt=%s, url=%s, size=%s, date=%s" % (self.title, self.excerpt, self.url, self.size, self.date)

class MaayResult:
    def __init__(self, document_id, score, relevance, popularity, date, state):
        self.document_id = document_id
        self.score = score
        self.relevance = relevance
        self.popularity = popularity
        self.date = date
        self.sent = 0
        self.state = state

def desc_cmp(x, y):
    if x < y:
        return 1
    if y < x:
        return -1
    return 0

def result_date_cmp(x, y):
    return desc_cmp(x.date, y.date)

def result_score_cmp(x, y):
    return desc_cmp(x.score, y.score)

class ResultSpool:

    def __init__(self, requester_node_id, query_id, search_query, r, min_score, expected_result_count, TTL, forwarding_node_count, query_time, visible=False):
        self.__node_id = requester_node_id
        self.__query_id = query_id
        self.__label = tools.query_str(search_query)

        self.__search_query = []
        for w in search_query:
            self.__search_query.append(globalvars.accent.translate(w).lower())

        self.__range = r
        self.__query_time = query_time
        # format of a result : (document_id, score, sent)
        self.__resultByID = {}

        self.__results = []

        self.__min_score = min_score
        self.__expected_result_count = expected_result_count
        self.__sent_result_count = 0
        self.__TTL = TTL
        self.__forwarding_node_count = forwarding_node_count
        self.__query_time = query_time

#               self.__sort_results = self.__results
        self.__private_document_count = 0
        self.__published_document_count = 0
        self.__cached_document_count = 0
        
        self.__result_count = 0
        
        self.__search_range_filter = None
        self.__file_type_filter = None
        self.__filtered_results = []
        self.__sort_policy = resultspool.SCORE_SORTED

        self.__filtered_result_count = {
                constants.ALL_SEARCH_RANGE: [ 0, 0, 0, 0, 0 ],
                constants.PRIVATE_SEARCH_RANGE: [ 0, 0, 0, 0, 0 ],
                constants.CACHED_SEARCH_RANGE: [ 0, 0, 0, 0, 0 ],
                constants.KNOWN_SEARCH_RANGE: [ 0, 0, 0, 0, 0 ],
                constants.PUBLISHED_SEARCH_RANGE: [ 0, 0, 0, 0, 0 ]}

    # TODO: remove this function
    def __dichotomy(self, results, value):
        start = 0
        end = len(results)
        while start < end:
            i = (start + end) >> 1
            if results[i].score > value:
                start = i + 1
            else:
                end = i
        return start


    def getExpectedResultCount(self):
        return self.__expected_result_count

    def getResults(self, sort_policy = resultspool.SCORE_SORTED):
        if sort_policy != self.__sort_policy:
            print "policy = %s" % sort_policy
            if sort_policy == resultspool.SCORE_SORTED:
                print "x, y = %s" % self.__results
                self.__results.sort(lambda x, y: desc_cmp(x.score, y.score))
            elif sort_policy == resultspool.DATE_SORTED:
                print "sort by date"
                self.__results.sort(lambda x, y: desc_cmp(x.date, y.date))

            self.__sort_policy = sort_policy
        return  self.__results

    def updateFilteredResultCount(self):
        self.__updateFilteredResultCount()

    def __updateFilteredResultCount(self):
        self.__filtered_result_count = {
                constants.ALL_SEARCH_RANGE: [ 0, 0, 0, 0, 0 ],
                constants.PRIVATE_SEARCH_RANGE: [ 0, 0, 0, 0, 0 ],
                constants.CACHED_SEARCH_RANGE: [ 0, 0, 0, 0, 0 ],
                constants.KNOWN_SEARCH_RANGE: [ 0, 0, 0, 0, 0 ],
                constants.PUBLISHED_SEARCH_RANGE: [ 0, 0, 0, 0, 0 ]
                                        }
        for result in self.__results:
            file_type = NO_RESULT_FILTER
            self.__filtered_result_count[result.state][file_type] += 1
            self.__filtered_result_count[constants.ALL_SEARCH_RANGE][NO_RESULT_FILTER] += 1
    
    def getFilteredResults(self, search_range_filter = constants.ALL_SEARCH_RANGE, file_type_filter = NO_RESULT_FILTER, sort_policy = resultspool.SCORE_SORTED):
        change = False
        if self.__filtered_result_count[constants.ALL_SEARCH_RANGE][NO_RESULT_FILTER] != len(self.__results):
            self.__updateFilteredResultCount()
            change = True


        if change == False and search_range_filter == self.__search_range_filter and file_type_filter == self.__file_type_filter:
            if sort_policy == self.__sort_policy:
                return self.__filtered_results
        else:           
            self.__search_range_filter = search_range_filter
            self.__file_type_filter = file_type_filter

            self.__filtered_results = []
            for result in self.__results:
                if (result.state & search_range_filter) != 0:
                    self.__filtered_results.append(result)

        self.__sort_policy = sort_policy

        if sort_policy == resultspool.SCORE_SORTED:
            self.__filtered_results.sort(result_score_cmp)
        else:
            self.__filtered_results.sort(result_date_cmp)
        return self.__filtered_results
        
    def getFilteredResultCount(self, search_range_filter = constants.ALL_SEARCH_RANGE, file_type_filter = NO_RESULT_FILTER):
        return self.__filtered_result_count[search_range_filter][file_type_filter]

    def getResultCount(self):
        return len(self.__results)


    def addResult(self, result):
        # check if document is not already in the list
        if self.__range in (constants.INTERNET_SEARCH_RANGE, constants.INTRANET_SEARCH_RANGE):
            self.__results.append(result)
            return

        result2 = self.__resultByID.get(result.document_id)
        if result2:
            return

        index = self.__dichotomy(self.__results, result.score)
        self.__results.insert(index, result)
        self.__resultByID[result.document_id] = result

    def getQuery(self):
        return self.__search_query

    def getQueryID(self):
        return self.__query_id

    def getResultCount(self):
        return len(self.__results)

#       def getFilteredResultCount(self, state):
#               return len(self.__filteredResults[state])

#       def getFilteredResults(self, state, sort_policy = resultspool.SCORE_SORTED):
#               if sort_policy != self.__filteredResultSortedPolicy[state]:
#                       if sort_policy == resultspool.SCORE_SORTED:
#                               self.__filteredResults[state].sort(result_date_cmp)
#                       elif sort_policy == resultspool.DATE_SORTED:
#                               self.__filteredResults[state].sort(result_date_cmp)
#                       self.__filteredResultSortedPolicy[state] = sort_policy
#       
#               return self.__filteredResults[state]

    def getExpectedResultCount(self):
        return len(self.__results)

    def getQueryTime(self):
        return self.__query_time

    def getRange(self):
        return self.__range

    def getNodeID(self):
        return self.__node_id

    def getBestUnsentResults(self):
        documentIDs = [r.document_id for r in self.__results if r.sent == 0][:self.__expected_result_count - self.__sent_result_count]
        self.__sent_result_count = len(documentIDs)
        return documentIDs

    def getSentResultCount(self):
        return self.__sent_result_count

    def getLabel(self):
        return self.__label
