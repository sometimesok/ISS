;(function() {
  function wrap($, thanks, Editor) {
    $(function() {
      $('.editor').each(function(_, el) {
        new Editor(el);
      });

      $('body').on('click', '.quote', function(e) {
        e.preventDefault();

        var quoteFetchUrl = $(e.target).attr('data-bbc-url'),
          editor = $('.quick-reply').data('editor');

        $.getJSON(quoteFetchUrl)
          .done(function(data) {
            editor.addQuote(data.content);
          })
          .fail(function(data) {
            alert('Failed to fetch quote.');
          });
      });

      $('.thread').on('submit', '.thank-action-form', function(e) {
        e.preventDefault();
        var button = $(e.currentTarget).find('.thank-action');
        thanks.handleThankIntention(button);
      });
    });
  }

  define([
    'jquery',
    'thanks',
    'editor'
  ], wrap);
})();

