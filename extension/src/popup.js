/**
 * Popup script for X Network Exporter
 * Handles UI interactions and communicates with content script
 */

// DOM Elements
const elements = {
  targetUsername: document.getElementById('targetUsername'),
  targetUserId: document.getElementById('targetUserId'),
  maxTweets: document.getElementById('maxTweets'),
  delayMs: document.getElementById('delayMs'),
  minViews: document.getElementById('minViews'),
  includeReplies: document.getElementById('includeReplies'),
  requestTemplateJson: document.getElementById('requestTemplateJson'),
  btnCapture: document.getElementById('btnCapture'),
  btnStart: document.getElementById('btnStart'),
  btnStop: document.getElementById('btnStop'),
  btnExport: document.getElementById('btnExport'),
  btnReset: document.getElementById('btnReset'),
  statusText: document.getElementById('statusText'),
  tweetCount: document.getElementById('tweetCount'),
  pageCount: document.getElementById('pageCount'),
  errorMessage: document.getElementById('errorMessage'),
  templateHeader: document.getElementById('templateHeader'),
  templateArrow: document.getElementById('templateArrow'),
  templateContent: document.getElementById('templateContent'),
  captureStatus: document.getElementById('captureStatus'),
  captureIcon: document.getElementById('captureIcon'),
  captureText: document.getElementById('captureText'),
  captureHint: document.getElementById('captureHint')
};

// State
let isRunning = false;
let currentTabId = null;
let hasCapturedTemplate = false;

// Initialize
document.addEventListener('DOMContentLoaded', async () => {
  await loadSavedConfig();
  await getCurrentTab();
  await checkCapturedTemplate();
  setupEventListeners();
  setupCollapsible();
});

// Load saved configuration from storage
async function loadSavedConfig() {
  try {
    const result = await chrome.storage.local.get([
      'targetUsername',
      'targetUserId',
      'maxTweets',
      'delayMs',
      'minViews',
      'includeReplies',
      'requestTemplateJson'
    ]);
    
    if (result.targetUsername) elements.targetUsername.value = result.targetUsername;
    if (result.targetUserId) elements.targetUserId.value = result.targetUserId;
    if (result.maxTweets) elements.maxTweets.value = result.maxTweets;
    if (result.delayMs) elements.delayMs.value = result.delayMs;
    if (result.minViews !== undefined) elements.minViews.value = result.minViews;
    if (result.includeReplies !== undefined) elements.includeReplies.checked = result.includeReplies;
    if (result.requestTemplateJson) elements.requestTemplateJson.value = result.requestTemplateJson;
  } catch (err) {
    console.error('Failed to load config:', err);
  }
}

// Check if we have a captured template
async function checkCapturedTemplate() {
  try {
    const result = await chrome.storage.local.get(['capturedTemplate', 'capturedAt', 'capturedUserId']);
    
    if (result.capturedTemplate) {
      hasCapturedTemplate = true;
      updateCaptureStatus(true, result.capturedAt);
      
      // Auto-fill userId if captured
      if (result.capturedUserId && !elements.targetUserId.value) {
        elements.targetUserId.value = result.capturedUserId;
      }
    } else {
      updateCaptureStatus(false);
    }
  } catch (err) {
    console.error('Failed to check captured template:', err);
  }
}

// Update capture status display
function updateCaptureStatus(captured, timestamp = null) {
  hasCapturedTemplate = captured;
  
  if (captured) {
    elements.captureStatus.classList.add('captured');
    elements.captureIcon.textContent = '✓';
    elements.captureIcon.style.color = '#00ba7c';
    elements.captureText.textContent = 'Request template captured!';
    elements.captureText.style.color = '#00ba7c';
    
    if (timestamp) {
      const date = new Date(timestamp);
      elements.captureHint.textContent = `Captured at ${date.toLocaleTimeString()} - Ready to export`;
    } else {
      elements.captureHint.textContent = 'Ready to export';
    }
  } else {
    elements.captureStatus.classList.remove('captured');
    elements.captureIcon.textContent = '○';
    elements.captureIcon.style.color = '#ffad1f';
    elements.captureText.textContent = 'Waiting for request capture...';
    elements.captureText.style.color = '#ffad1f';
    elements.captureHint.textContent = 'Enter a username and click "Capture" to auto-capture';
  }
}

// Save configuration to storage
async function saveConfig() {
  try {
    await chrome.storage.local.set({
      targetUsername: elements.targetUsername.value,
      targetUserId: elements.targetUserId.value,
      maxTweets: parseInt(elements.maxTweets.value, 10),
      delayMs: parseInt(elements.delayMs.value, 10),
      minViews: parseInt(elements.minViews.value, 10) || 0,
      includeReplies: elements.includeReplies.checked,
      requestTemplateJson: elements.requestTemplateJson.value
    });
  } catch (err) {
    console.error('Failed to save config:', err);
  }
}

// Get current active tab
async function getCurrentTab() {
  try {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    if (tab) {
      currentTabId = tab.id;
      // Don't require being on x.com for capture button to work
    }
  } catch (err) {
    console.error('Failed to get current tab:', err);
    showError('Could not access current tab.');
  }
}

// Setup event listeners
function setupEventListeners() {
  elements.btnCapture.addEventListener('click', captureProfile);
  elements.btnStart.addEventListener('click', startExport);
  elements.btnStop.addEventListener('click', stopExport);
  elements.btnExport.addEventListener('click', exportData);
  elements.btnReset.addEventListener('click', resetExport);
  
  // Save config on input change
  const inputs = [
    elements.targetUsername,
    elements.targetUserId,
    elements.maxTweets,
    elements.delayMs,
    elements.minViews,
    elements.includeReplies,
    elements.requestTemplateJson
  ];
  
  inputs.forEach(input => {
    input.addEventListener('change', saveConfig);
  });
  
  // Listen for messages from content script
  chrome.runtime.onMessage.addListener(handleMessage);
  
  // Listen for storage changes (for cross-tab capture updates)
  chrome.storage.onChanged.addListener((changes, namespace) => {
    if (namespace === 'local' && changes.capturedTemplate) {
      if (changes.capturedTemplate.newValue) {
        checkCapturedTemplate();
      }
    }
  });
}

// Setup collapsible template section
function setupCollapsible() {
  elements.templateHeader.addEventListener('click', () => {
    elements.templateContent.classList.toggle('expanded');
    elements.templateArrow.classList.toggle('expanded');
  });
}

// Capture profile - open new tab with user's profile
async function captureProfile() {
  const username = elements.targetUsername.value.trim();
  
  if (!username) {
    showError('Please enter a username first.');
    return;
  }
  
  // Save the username
  await saveConfig();
  
  // Open the profile page with replies in a new tab
  const profileUrl = `https://x.com/${username}/with_replies`;
  
  try {
    // Create new tab
    const tab = await chrome.tabs.create({ url: profileUrl, active: true });
    
    // Update status
    elements.captureHint.textContent = `Opening ${username}'s profile... Scroll will trigger capture.`;
    
    // Close popup (optional - user can keep it open)
    // window.close();
    
  } catch (err) {
    console.error('Failed to open profile:', err);
    showError('Failed to open profile page.');
  }
}

// Handle messages from content script
function handleMessage(message, sender, sendResponse) {
  console.log('Popup received message:', message);
  
  switch (message.type) {
    case 'XNE_PROGRESS':
      updateProgress(message.payload);
      break;
    case 'XNE_DONE':
      handleDone(message.payload);
      break;
    case 'XNE_ERROR':
      handleError(message.payload);
      break;
    case 'XNE_DATA':
      handleDataReceived(message.payload);
      break;
    case 'XNE_TEMPLATE_CAPTURED':
      updateCaptureStatus(true, message.payload.timestamp);
      // Auto-fill userId if present
      if (message.payload.userId) {
        elements.targetUserId.value = message.payload.userId;
        saveConfig();
      }
      break;
    case 'XNE_TEMPLATE':
      if (message.payload.hasCaptured) {
        updateCaptureStatus(true);
      }
      break;
  }
  
  return true;
}

// Start export process
async function startExport() {
  // Validate inputs
  const targetUserId = elements.targetUserId.value.trim();
  const requestTemplateJson = elements.requestTemplateJson.value.trim();
  
  if (!targetUserId) {
    showError('Target User ID is required. Click "Capture" first to auto-fill it.');
    return;
  }
  
  // Check if we have a template (either manual or captured)
  if (!requestTemplateJson && !hasCapturedTemplate) {
    showError('No request template available. Click "Capture" first.');
    return;
  }
  
  // Parse manual template if provided
  let template = null;
  if (requestTemplateJson) {
    try {
      template = JSON.parse(requestTemplateJson);
    } catch (err) {
      showError('Invalid JSON in Manual Template: ' + err.message);
      return;
    }
  }
  
  // Save config
  await saveConfig();
  
  // Build config
  const config = {
    targetUsername: elements.targetUsername.value.trim(),
    targetUserId: targetUserId,
    maxTweets: parseInt(elements.maxTweets.value, 10) || 2000,
    delayMs: parseInt(elements.delayMs.value, 10) || 750,
    minViews: parseInt(elements.minViews.value, 10) || 0,
    includeReplies: elements.includeReplies.checked,
    template: template // Will be null if using auto-captured
  };
  
  // Update UI
  isRunning = true;
  updateUIState();
  hideError();
  setStatus('Starting...', 'running');
  
  // Get the active tab (should be on x.com)
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  
  if (!tab || !tab.url || !tab.url.startsWith('https://x.com')) {
    showError('Please navigate to x.com first, or use the Capture button.');
    isRunning = false;
    updateUIState();
    return;
  }
  
  currentTabId = tab.id;
  
  // Send message to content script
  try {
    await chrome.tabs.sendMessage(currentTabId, {
      type: 'XNE_START',
      payload: config
    });
  } catch (err) {
    console.error('Failed to send start message:', err);
    showError('Failed to start export. Make sure you are on x.com and refresh the page.');
    isRunning = false;
    updateUIState();
  }
}

// Stop export process
async function stopExport() {
  try {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    if (tab) {
      await chrome.tabs.sendMessage(tab.id, { type: 'XNE_STOP' });
    }
    isRunning = false;
    setStatus('Stopped', '');
    updateUIState();
  } catch (err) {
    console.error('Failed to send stop message:', err);
  }
}

// Export data
async function exportData() {
  try {
    setStatus('Requesting data...', 'running');
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    if (tab) {
      await chrome.tabs.sendMessage(tab.id, { type: 'XNE_GET_DATA' });
    }
  } catch (err) {
    console.error('Failed to request data:', err);
    showError('Failed to request data. Try refreshing the page.');
  }
}

// Reset export
async function resetExport() {
  try {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    if (tab && tab.url && tab.url.startsWith('https://x.com')) {
      await chrome.tabs.sendMessage(tab.id, { type: 'XNE_RESET' });
    }
    elements.tweetCount.textContent = '0';
    elements.pageCount.textContent = '0';
    setStatus('Idle', '');
    hideError();
    elements.btnExport.disabled = true;
  } catch (err) {
    console.error('Failed to send reset message:', err);
  }
}

// Update progress display
function updateProgress(payload) {
  if (payload.count !== undefined) {
    elements.tweetCount.textContent = payload.count.toString();
  }
  if (payload.pages !== undefined) {
    elements.pageCount.textContent = payload.pages.toString();
  }
  setStatus('Running...', 'running');
}

// Handle export completion
function handleDone(payload) {
  isRunning = false;
  elements.tweetCount.textContent = payload.count.toString();
  setStatus('Complete', 'done');
  elements.btnExport.disabled = false;
  updateUIState();
}

// Handle error from content script
function handleError(payload) {
  isRunning = false;
  showError(payload.message || 'An unknown error occurred.');
  setStatus('Error', 'error');
  updateUIState();
}

// Handle data received for export
function handleDataReceived(payload) {
  const tweets = payload.tweets || [];
  
  if (tweets.length === 0) {
    showError('No tweets to export.');
    setStatus('Idle', '');
    return;
  }
  
  // Generate filename with .jsonl extension (JSON Lines format for Python import)
  const username = elements.targetUsername.value.trim() || 'account';
  const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19);
  const filename = `${username}_tweets_${timestamp}.jsonl`;
  
  // Create JSONL content (one JSON object per line, no pretty printing)
  // This format is expected by Python's tweetdna import command
  const jsonlContent = tweets.map(tweet => JSON.stringify(tweet)).join('\n');
  const blob = new Blob([jsonlContent], { type: 'application/x-ndjson' });
  const url = URL.createObjectURL(blob);
  
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
  
  setStatus(`Exported ${tweets.length} tweets`, 'done');
}

// Update UI state based on isRunning
function updateUIState() {
  elements.btnStart.disabled = isRunning;
  elements.btnStop.disabled = !isRunning;
  elements.btnCapture.disabled = isRunning;
  elements.targetUsername.disabled = isRunning;
  elements.targetUserId.disabled = isRunning;
  elements.maxTweets.disabled = isRunning;
  elements.delayMs.disabled = isRunning;
  elements.minViews.disabled = isRunning;
  elements.includeReplies.disabled = isRunning;
  elements.requestTemplateJson.disabled = isRunning;
}

// Set status text
function setStatus(text, className) {
  elements.statusText.textContent = text;
  elements.statusText.className = 'status-value';
  if (className) {
    elements.statusText.classList.add(className);
  }
}

// Show error message
function showError(message) {
  elements.errorMessage.textContent = message;
  elements.errorMessage.classList.add('visible');
}

// Hide error message
function hideError() {
  elements.errorMessage.textContent = '';
  elements.errorMessage.classList.remove('visible');
}
