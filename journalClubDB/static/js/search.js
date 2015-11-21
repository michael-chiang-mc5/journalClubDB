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

  // pagination functionality
  $(".page").click(function() {

    // create pubmed esearch link
    var new_page = $( this ).next('input').val();
    retstart = (new_page - 1) * max_results_per_page
    var search_str = $( '#pubmed-search-text' ).val()
    var search_str_safe = search_str.replace(" ", "+"); // TODO: edge case where user wants to search for + sign
    var pubmed_search_link = 'http://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pubmed&term=' + search_str_safe + '&retmode=json&retmax=' + max_results_per_page + '&retstart=' + retstart

    // Execute search
    $.getJSON(pubmed_search_link, function(data){
      // Get pubmed ids of search results
      var ids = data.esearchresult.idlist;
      var count = data.esearchresult.count;
      // Create a link that fetches pubmed data of corresponding ids
      var efetch_link = 'http://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=pubmed&id=' + ids + '&rettype=medline&retmode=xml'
      // get xml data from pubmed, convert it to json, store it in a form, then submit it to search
      $.get( efetch_link, function( data ) {
        var json_str = JSON.stringify(xml2json(data));
        $("#pubmed-search-text").val(json_str)
        $("#search-bar-placeholder").val(search_str)
        $("#pubmed-search-count").val(count)
        $("#new-page").val(new_page)
        $("#pubmed-search-form").submit()
      });
    });

  });

  // Search bar functionality
  $(".text-search").keyup(function (e) {
    if (e.keyCode == 13) {
      // If enter is pressed in the search bar, get the search string and create a link that executes a pubmed search
      var search_str = $(this).val()
      var search_str_safe = search_str.replace(" ", "+"); // TODO: edge case where user wants to search for + sign
      var pubmed_search_link = 'http://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pubmed&term=' + search_str_safe + '&retmode=json&retmax=' + max_results_per_page
      // Execute search
      $.getJSON(pubmed_search_link, function(data){
        // Get pubmed ids of search results
        var ids = data.esearchresult.idlist;
        var count = data.esearchresult.count;
        // Create a link that fetches pubmed data of corresponding ids
        var efetch_link = 'http://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=pubmed&id=' + ids + '&rettype=medline&retmode=xml'
        // get xml data from pubmed, convert it to json, store it in a form, then submit it to search
        $.get( efetch_link, function( data ) {
          var json_str = JSON.stringify(xml2json(data));
          $("#pubmed-search-text").val(json_str)
          $("#search-bar-placeholder").val(search_str)
          $("#pubmed-search-count").val(count)
          $("#new-page").val(1)
          $("#pubmed-search-form").submit()
        });
      });
    }
  });

});
