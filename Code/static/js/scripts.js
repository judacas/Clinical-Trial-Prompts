function toggleSidebar() {
	var sidebar = document.getElementById("sidebar");
	var content = document.getElementById("content");
	sidebar.classList.toggle("show-sidebar");
	content.classList.toggle("show-content");
  }
  
  function fetchTrials() {
	$.get('/list_trials', function(data) {
	  var trialsList = $('#trials-list');
	  trialsList.empty();
	  data.trials.forEach(function(trial) {
		trialsList.append('<p>' + trial + '</p>');
	  });
	});
  }
  
  document.addEventListener('DOMContentLoaded', function() {
	var trialsForm = document.getElementById('trials-form');
  
	if (trialsForm) {
	  trialsForm.addEventListener('submit', function(event) {
		event.preventDefault();
		var formData = new FormData(trialsForm);
		$.ajax({
		  url: '/process_trials',
		  type: 'POST',
		  data: formData,
		  processData: false,
		  contentType: false,
		  success: function(response) {
			renderResults(response.result.Trials);
		  },
		  error: function() {
			alert('Error processing trials.');
		  }
		});
	  });
	}
  });
  
  function loadSubfolders(folder) {
	if (folder) {
	  $.get('/list_subfolders', { folder: folder }, function(data) {
		var subfolderContainer = document.getElementById('subfolder-container');
		var subfolderSelect = document.getElementById('trials_folder');
		subfolderSelect.innerHTML = ''; // Clear previous options
  
		data.subfolders.forEach(function(subfolder) {
		  var option = document.createElement('option');
		  option.value = subfolder;
		  option.textContent = subfolder;
		  subfolderSelect.appendChild(option);
		});
  
		subfolderContainer.style.display = 'block';
	  });
	} else {
	  document.getElementById('subfolder-container').style.display = 'none';
	}
  }
  
  function renderResults(trials) {
	var resultsDiv = document.getElementById('results');
	resultsDiv.innerHTML = ''; // Clear previous results
	var accordion = document.createElement('div');
	accordion.classList.add('accordion');
	accordion.setAttribute('id', 'trialsAccordion');
  
	trials.forEach(function(trial, index) {
	  var card = document.createElement('div');
	  card.classList.add('card');
  
	  var cardHeader = document.createElement('div');
	  cardHeader.classList.add('card-header');
	  cardHeader.setAttribute('id', 'heading' + index);
  
	  var h5 = document.createElement('h5');
	  h5.classList.add('mb-0');
  
	  var button = document.createElement('button');
	  button.classList.add('btn', 'btn-link');
	  button.setAttribute('type', 'button');
	  button.setAttribute('data-toggle', 'collapse');
	  button.setAttribute('data-target', '#collapse' + index);
	  button.setAttribute('aria-expanded', 'true');
	  button.setAttribute('aria-controls', 'collapse' + index);
	  button.textContent = `${trial.nctId} - ${trial.title}`;
  
	  h5.appendChild(button);
	  cardHeader.appendChild(h5);
	  card.appendChild(cardHeader);
  
	  var collapse = document.createElement('div');
	  collapse.id = 'collapse' + index;
	  collapse.classList.add('collapse');
	  collapse.setAttribute('aria-labelledby', 'heading' + index);
	  collapse.setAttribute('data-parent', '#trialsAccordion');
  
	  var cardBody = document.createElement('div');
	  cardBody.classList.add('card-body');
	  cardBody.textContent = JSON.stringify(trial, null, 2); // Display JSON nicely
  
	  collapse.appendChild(cardBody);
	  card.appendChild(collapse);
	  accordion.appendChild(card);
	});
  
	resultsDiv.appendChild(accordion);
  }
  