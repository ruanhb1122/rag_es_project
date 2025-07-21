// 页面加载完成后执行
document.addEventListener('DOMContentLoaded', function() {
    // 初始化上传表单
    initUploadForm();
    // 初始化搜索表单
    initSearchForm();
    // 初始化搜索建议
    initSearchSuggestions();
});

// 初始化上传表单
function initUploadForm() {
    const uploadForm = document.getElementById('uploadForm');
    if (!uploadForm) return;

    uploadForm.addEventListener('submit', function(e) {
        e.preventDefault();

        const formData = new FormData(this);
        const resultDiv = document.getElementById('result');

        console.log('formData.....', formData);

        // 显示加载状态
        resultDiv.innerHTML = '<div class="loading">正在上传...</div>';

        // 发送请求
        fetch('/api/documents/upload', {
            method: 'POST',
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                resultDiv.innerHTML = `
                    <div class="success">
                        <h3>上传成功</h3>
                        <p>文档ID: ${data.document_id}</p>
                        <p>文档名称: ${formData.get('file').name}</p>
                    </div>
                `;
                uploadForm.reset();
            } else {
                resultDiv.innerHTML = `<div class="error">错误: ${data.error}</div>`;
            }
        })
        .catch(error => {
            resultDiv.innerHTML = `<div class="error">上传失败: ${error.message}</div>`;
        });
    });
}

// 初始化搜索表单
function initSearchForm() {
    const searchForm = document.getElementById('searchForm');
    if (!searchForm) return;

    searchForm.addEventListener('submit', function(e) {
        e.preventDefault();

        const formData = new FormData(searchForm);
        const params = new URLSearchParams();

        formData.forEach((value, key) => {
            params.append(key, value);
        });

        const resultsContainer = document.getElementById('resultsContainer');
        resultsContainer.innerHTML = '<div class="loading">正在搜索...</div>';

        // 发送搜索请求
        fetch(`/api/search?${params.toString()}`)
        .then(response => response.json())
        .then(data => {
            if (data.results && data.results.length > 0) {
                let html = '';
                data.results.forEach((result, index) => {
                    html += `
                        <div class="result-item">
                            <h4>结果 ${index + 1} (得分: ${result.score.toFixed(4)})</h4>
                            <p class="chunk-id">分块ID: ${result.chunk_id}</p>
                            <p class="document-id">文档ID: ${result.document_id}</p>
                            <div class="content">${result.content.substring(0, 300)}${result.content.length > 300 ? '...' : ''}</div>
                        </div>
                    `;
                });
                resultsContainer.innerHTML = html;
            } else {
                resultsContainer.innerHTML = '<div class="no-results">未找到匹配结果</div>';
            }
        })
        .catch(error => {
            resultsContainer.innerHTML = `<div class="error">搜索失败: ${error.message}</div>`;
        });
    });
}

// 初始化搜索建议
function initSearchSuggestions() {
    const searchInput = document.getElementById('searchQuery');
    const suggestionsDiv = document.getElementById('searchSuggestions');
    if (!searchInput || !suggestionsDiv) return;

    searchInput.addEventListener('input', function() {
        const query = this.value.trim();
        const kbId = document.getElementById('searchKbId').value.trim();

        if (query.length < 2 || !kbId) {
            suggestionsDiv.innerHTML = '';
            return;
        }

        // 获取搜索建议
        fetch(`/api/search/suggestions?kb_id=${kbId}&query=${encodeURIComponent(query)}`)
        .then(response => response.json())
        .then(data => {
            if (data.suggestions && data.suggestions.length > 0) {
                let html = '<h4>搜索建议:</h4><ul>';
                data.suggestions.forEach(suggestion => {
                    html += `<li><a href="#" data-suggestion="${suggestion}">${suggestion}</a></li>`;
                });
                html += '</ul>';
                suggestionsDiv.innerHTML = html;

                // 绑定建议点击事件
                document.querySelectorAll('#searchSuggestions a').forEach(link => {
                    link.addEventListener('click', function(e) {
                        e.preventDefault();
                        searchInput.value = this.getAttribute('data-suggestion');
                    });
                });
            } else {
                suggestionsDiv.innerHTML = '';
            }
        })
        .catch(error => {
            console.error('获取搜索建议失败:', error);
        });
    });
}

//
//
// document.getElementById('uploadForm').addEventListener('submit', function(e) {
//             e.preventDefault();
//
//             const formData = new FormData(this);
//             const resultDiv = document.getElementById('result');
//
//             // 显示加载状态
//             resultDiv.style.display = 'block';
//             resultDiv.className = 'result';
//             resultDiv.innerHTML = '上传中...';
//
//             // 发送请求
//             fetch('/upload', {
//                 method: 'POST',
//                 body: formData
//             })
//             .then(response => response.json())
//             .then(data => {
//                 if (data.success) {
//                     resultDiv.className = 'result success';
//                     resultDiv.innerHTML = `
//                         <h3>上传成功!</h3>
//                         <p><strong>MinIO URL:</strong> <a href="${data.minio_url}" target="_blank">${data.minio_url}</a></p>
//                         <p><strong>预签名URL:</strong> <a href="${data.presigned_url}" target="_blank">${data.presigned_url}</a></p>
//                         <p><strong>文档切块数量:</strong> ${data.document_chunks}</p>
//                     `;
//                 } else {
//                     resultDiv.className = 'result error';
//                     resultDiv.innerHTML = `<h3>上传失败</h3><p>${data.error}</p>`;
//                 }
//             })
//             .catch(error => {
//                 resultDiv.className = 'result error';
//                 resultDiv.innerHTML = `<h3>发生错误</h3><p>${error.message}</p>`;
//             });
//         });