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
        self.entries = []

    def __str__(self):
        return "Provides functionality to interface with pubmed."

    def getRecords(self,search_str,maxNumberOfRecords):
        ids = self.getIDs(search_str,maxNumberOfRecords)
        handle = Entrez.efetch(db="pubmed", id=ids, rettype="medline",retmode="text")
        records = Medline.parse(handle)
        rn = []
        for record in records:
            pubmedEntry = PubmedEntry()
            pubmedEntry.title = record.get("TI",None)
            pubmedEntry.author = record.get("AU",None)
            pubmedEntry.journal = record.get("TA",None)
            pubmedEntry.volume = record.get("VI",None)
            pubmedEntry.number = record.get("IP",None)
            pubmedEntry.pages = record.get("PG",None)
            pubmedEntry.date = record.get("DP", None)
            pubmedEntry.fullSource = record.get("SO",None)
            pubmedEntry.keywords = record.get("OT", None)
            pubmedEntry.abstract = record.get("AB", None)
            pubmedEntry.doi = record.get("LID", None)
            pubmedEntry.fullAuthorNames = record.get("FAU", None)
            pubmedEntry.pubmedID = record.get("PMID", None)
            self.entries.append(pubmedEntry)

    def getIDs(self,search_str,maxNumberOfRecords):
        handle = Entrez.esearch(db="pubmed", term=search_str, retmax=maxNumberOfRecords)
        record = Entrez.read(handle)
        idlist = record["IdList"]
        return idlist

class PubmedEntry():

    def __init__(self):
        self.title = None
        self.author = None
        self.journal = None
        self.volume = None
        self.number = None
        self.pages = None
        self.date = None
        self.fullCite = None
        self.keywords = None
        self.abstract = None
        self.doi = None
        self.fullAuthorNames = None
        self.pubmedID = None

    def __str__(self):
        return "Stores a single pubmed citation"
