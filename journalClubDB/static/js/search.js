$(document).ready(function() {


  $(".import-button").click(function() {
    var b = $( this )
    var f = b.next('form');
    var url = f.attr( 'action' );
    if ( b.hasClass('import-button')) { // this is required because click doesn't detect changes to class
      $.ajax({
        type: "POST",
        url: url,
        data: f.serialize(), // serializes the form's elements.
        success: function(data) {
          b.removeClass('import-button')
          b.parent().attr("href",data)
          b.html("Click to discuss this paper!")
        }
      });
    }
  });

  /* deprecated way of importing citations */
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



  $(".text-search").keyup(function (e) {
    if (e.keyCode == 13) {
      // If enter is pressed in the search bar, get the search string and create a link that executes a pubmed search
      var search_str = $(this).val()
      var search_str_safe = search_str.replace(" ", "+"); // TODO: edge case where user wants to search for + sign
      var pubmed_search_link = 'http://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pubmed&term=' + search_str_safe + '&retmode=json'

      // Execute search
      $.getJSON(pubmed_search_link, function(data){
        // Get pubmed ids of search results
        var ids = data.esearchresult.idlist;
        // Create a link that fetches pubmed data of corresponding ids
        var efetch_link = 'http://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=pubmed&id=' + ids + '&rettype=medline&retmode=xml'
        // get xml data from pubmed, convert it to json, store it in a form, then submit it to search
        $.get( efetch_link, function( data ) {
          var json_str = JSON.stringify(xml2json(data));
          $("#pubmed-search-text").val(json_str)
          $("#search-bar-placeholder").val(search_str)
          $("#pubmed-search-form").submit()
        });
      });
    }
  });

});
