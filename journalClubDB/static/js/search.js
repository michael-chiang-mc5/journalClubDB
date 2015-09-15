// On button click
// url_js, csrf_js are variables that need to be set in search.html
// since django templating does not apply to javascript files

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

});
