const dropZone = document.getElementById('drop-zone');
const fileInput = document.getElementById('file-input');
const browseBtn = document.getElementById('browse-btn');
const fileList = document.getElementById('file-list');
const processBtn = document.getElementById('process-btn');
const syllabusInput = document.getElementById('syllabus-input');
const statusSection = document.getElementById('status-section');
const statusText = document.getElementById('status-text');

let selectedFiles = [];

// Drag & Drop Handling
dropZone.addEventListener('dragover', (e) => {
    e.preventDefault(); 
    dropZone.classList.add('dragover');
});
dropZone.addEventListener('dragleave', () => dropZone.classList.remove('dragover'));
dropZone.addEventListener('drop', (e) => {
    e.preventDefault(); 
    dropZone.classList.remove('dragover');
    if(e.dataTransfer.files.length) handleFiles(e.dataTransfer.files);
});

browseBtn.addEventListener('click', () => fileInput.click());
fileInput.addEventListener('change', () => {
    if(fileInput.files.length) handleFiles(fileInput.files);
});

function handleFiles(files) {
    for (let i = 0; i < files.length; i++) {
        selectedFiles.push(files[i]);
    }
    renderFileList();
}

function renderFileList() {
    fileList.innerHTML = '';
    selectedFiles.forEach((file, index) => {
        const item = document.createElement('div');
        item.className = 'file-item';
        item.innerHTML = `<span>${file.name}</span> <span class="remove" onclick="removeFile(${index})">&times;</span>`;
        fileList.appendChild(item);
    });
}

// Global scope remove function
window.removeFile = function(index) {
    selectedFiles.splice(index, 1);
    renderFileList();
}

// Processing
processBtn.addEventListener('click', async () => {
    const syllabus = syllabusInput.value.trim();
    if (selectedFiles.length === 0) return alert('Please upload at least one paper.');
    if (!syllabus) return alert('Please define your syllabus.');

    statusSection.style.display = 'block';
    processBtn.disabled = true;
    processBtn.style.opacity = '0.5';
    statusText.textContent = "Processing papers... This may take a while depending on file size.";

    const formData = new FormData();
    selectedFiles.forEach(file => formData.append('files', file));
    formData.append('syllabus', syllabus);
    const selectedOutputMode = document.querySelector('input[name="output-mode"]:checked');
    formData.append('output_mode', selectedOutputMode ? selectedOutputMode.value : 'clean');

    try {
        const response = await fetch('/api/upload', {
            method: 'POST',
            body: formData
        });

        if (!response.ok) {
            const errBody = await response.text();
            throw new Error('Failed to process papers ' + errBody);
        }

        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        const outputMode = selectedOutputMode ? selectedOutputMode.value : 'clean';
        a.download = outputMode === 'both'
            ? 'organized_papers_bundle.zip'
            : (outputMode === 'full' ? 'organized_papers_full.pdf' : 'organized_papers_clean.pdf');
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        a.remove();
        
        statusText.textContent = "Processing complete! Your file has been downloaded.";
        document.querySelector('.loader').style.display = 'none';
        
    } catch (error) {
        statusText.textContent = "Error: " + error.message;
        document.querySelector('.loader').style.display = 'none';
        console.error(error);
    } finally {
        processBtn.disabled = false;
        processBtn.style.opacity = '1';
        if(statusText.textContent.includes('complete')) {
            setTimeout(() => {
                statusSection.style.display = 'none';
                document.querySelector('.loader').style.display = 'block';
            }, 5000);
        }
    }
});
