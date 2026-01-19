/**
 * Background service worker for X Network Exporter
 * Uses webRequest API to capture actual network requests with all headers
 */

console.log('[XNE Background] Service worker started.');

// Store captured request data
let capturedRequest = null;

// Listen for UserTweetsAndReplies requests
chrome.webRequest.onBeforeSendHeaders.addListener(
  (details) => {
    if (!details.url.includes('UserTweetsAndReplies')) return;
    
    console.log('[XNE Background] Captured request:', details.url.substring(0, 80));
    
    // Parse the URL
    const urlObj = new URL(details.url);
    
    // Build headers object
    const headers = {};
    if (details.requestHeaders) {
      for (const header of details.requestHeaders) {
        headers[header.name.toLowerCase()] = header.value;
      }
    }
    
    // Parse variables from URL
    let variables = null;
    let features = null;
    let fieldToggles = null;
    
    const variablesParam = urlObj.searchParams.get('variables');
    const featuresParam = urlObj.searchParams.get('features');
    const fieldTogglesParam = urlObj.searchParams.get('fieldToggles');
    
    if (variablesParam) {
      try { variables = JSON.parse(variablesParam); } catch(e) {}
    }
    if (featuresParam) {
      try { features = JSON.parse(featuresParam); } catch(e) {}
    }
    if (fieldTogglesParam) {
      try { fieldToggles = JSON.parse(fieldTogglesParam); } catch(e) {}
    }
    
    // Store the captured request
    capturedRequest = {
      baseUrl: urlObj.origin + urlObj.pathname,
      method: details.method,
      headers: headers,
      variables: variables,
      features: features,
      fieldToggles: fieldToggles,
      capturedAt: Date.now(),
      userId: variables?.userId
    };
    
    console.log('[XNE Background] Template captured! UserId:', capturedRequest.userId);
    console.log('[XNE Background] Headers captured:', Object.keys(headers).length);
    
    // Save to storage
    chrome.storage.local.set({
      capturedTemplate: capturedRequest,
      capturedAt: capturedRequest.capturedAt,
      capturedUserId: capturedRequest.userId
    });
    
    // Notify any open popups
    chrome.runtime.sendMessage({
      type: 'XNE_TEMPLATE_CAPTURED',
      payload: {
        template: capturedRequest,
        timestamp: capturedRequest.capturedAt,
        userId: capturedRequest.userId
      }
    }).catch(() => {
      // Popup may not be open
    });
  },
  { urls: ['https://x.com/i/api/graphql/*/UserTweetsAndReplies*'] },
  ['requestHeaders']
);

// Handle messages
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  console.log('[XNE Background] Received message:', message.type);
  
  if (message.type === 'GET_CAPTURED_TEMPLATE') {
    sendResponse({ template: capturedRequest });
    return true;
  }
  
  if (message.type === 'OPEN_CAPTURE_TAB') {
    chrome.tabs.create({ url: message.url, active: true });
    sendResponse({ success: true });
    return true;
  }
  
  return false;
});

console.log('[XNE Background] Listening for UserTweetsAndReplies requests...');
