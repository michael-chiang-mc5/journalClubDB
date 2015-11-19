function iterateJSON(idlist, publications) {

    var id = idlist.pop();
    $.getJSON('http://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?db=pubmed&id='+id+'&retmode=json', function(summary){

        var citation = "";

        for(author in summary.result[id].authors){
            citation+=summary.result[id].authors[author].name+', ';
        }
        citation+=' \"'+summary.result[id].title+'\" <i>'+summary.result[id].fulljournalname+'</i> '+summary.result[id].volume+'.'+summary.result[id].issue+' ('+summary.result[id].pubdate+'): '+summary.result[id].pages+'.';

        console.log(citation);
        publications.push(citation);

        if(idlist.length!=0){
            iterateJSON(idlist, publications);
        }else{
            console.log(publications);
        }

    });
}

$(document).ready(function() {
  $( "form[id*='f_']" ).submit(function(event){

      var f_id = $(this).attr("id")
      var arr = f_id.split('_')
      var id = arr[1]
      $('#s_'+id).val("Saving")

      $.ajax({
           type:"POST",
           url: url_js,
           data: {
                  csrfmiddlewaretoken: csrf_js,
                  'title': $('#title_'+id).val(),
                  'author': $('#author_'+id).val(),
                  'journal': $('#journal_'+id).val(),
                  'volume': $('#volume_'+id).val(),
                  'number': $('#number_'+id).val(),
                  'pages': $('#pages_'+id).val(),
                  'date': $('#date_'+id).val(),
                  'fullSource': $('#fullSource_'+id).val(),
                  'keywords': $('#keywords_'+id).val(),
                  'abstract': $('#abstract_'+id).val(),
                  'doi': $('#doi_'+id).val(),
                  'fullAuthorNames': $('#fullAuthorNames_'+id).val(),
                  'pubmedID': $('#pubmedID_'+id).val(),
                  },
           success: function(data){
               $('#f_'+id).hide();
               $('#b_'+id).show();
               $('#b_'+id).html("View")
               $('#a_'+id).attr("href",data.new_citation_url)
           }
      });
      return false;
  });


  // check if enter pressed
  $(".text-search").keyup(function (e) {
      if (e.keyCode == 13) {
        var search_str = $(this).val()
        search_str = search_str.replace(" ", "+"); // TODO: edge case where user wants to search for + sign
        var pubmed_search_link = 'http://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pubmed&term=' + search_str + '&retmode=json'
        alert(pubmed_search_link)

        $.getJSON(pubmed_search_link, function(data){
          alert("in json")
          var ids = data.esearchresult.idlist;
          alert(ids)
          var efetch_str = 'http://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=pubmed&id=' + ids + '&rettype=medline&retmode=xml'
          alert(efetch_str) // http://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=pubmed&id=26576326,26572874,26568045,26565545,26562993,26561314,26560552,26549864,26549334,26544047,26528861,26528309,26527344,26523529,26521525,26519404,26512070,26508446,26504957,26500474&rettype=medline&retmode=xml
        });
      }
  });

});
