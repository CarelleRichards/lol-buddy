$(function() {
    $('[data-toggle="tooltip"]').tooltip()
})

 function setModal(trueOrFalse) {
        const modalDisplay = trueOrFalse ? 'flex' : 'none';
        const element = document.getElementById('loadingModal');
        if (element) {
          element.style.display = modalDisplay;
        }
      }