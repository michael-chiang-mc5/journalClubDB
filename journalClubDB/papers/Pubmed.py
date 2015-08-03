# This class require biopython
# Example usage:
# from Pubmed import PubmedInterface
# x = PubmedInterface()
# x.getRecords("Cell cycle adaptations of embryonic stem cells",10)

from Bio import Entrez
from Bio import Medline

class PubmedInterface():

    def __init__(self):
        Entrez.email = "michael.chiang.mc5@gmail.com"

    def __str__(self):
        return "Provides functionality to interface with pubmed."

    def testFunction(self):
        return "asdf"

    def getRecords(self,search_str,maxNumberOfRecords):
        ids = self.getIDs(search_str,maxNumberOfRecords)
        handle = Entrez.efetch(db="pubmed", id=ids, rettype="medline",retmode="text")
        records = Medline.parse(handle)
        rn = []
        for record in records:
            d = {'title'    : record.get("TI",None), \
                 'author'   : record.get("AU",None), \
                 'journal'  : record.get("TA",None), \
                 'volume'   : record.get("VI",None), \
                 'number'   : record.get("IP",None), \
                 'pages'    : record.get("PG",None), \
                 'date'     : record.get("DP", None), \
                 'fullCite' : record.get("SO",None), \
                 'keywords' : record.get("OT", None), \
                 'abstract' : record.get("AB", None), \
                 'doi'      : record.get("LID", None), \
                 'pubmedID' : record.get("PMID", None), \
                }
            rn.append(d)
        return rn

    def getIDs(self,search_str,maxNumberOfRecords):
        handle = Entrez.esearch(db="pubmed", term=search_str, retmax=maxNumberOfRecords)
        record = Entrez.read(handle)
        idlist = record["IdList"]
        return idlist
