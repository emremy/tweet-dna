/**
 * Content script for X Network Exporter
 * Handles message passing and provides captured template to injected.js
 */

(function() {
  'use strict';
  
  if (window.__XNE_CONTENT_INJECTED__) return;
  window.__XNE_CONTENT_INJECTED__ = true;
  
  console.log('[XNE Content] Content script loaded.');
  
  // Inject page scripts for export functionality
  function injectPageScripts() {
    if (document.getElementById('xne-injected-script')) return;
    
    const normalizeScript = document.createElement('script');
    normalizeScript.id = 'xne-normalize-script';
    normalizeScript.src = chrome.runtime.getURL('src/normalize.js');
    (document.head || document.documentElement).appendChild(normalizeScript);
    
    normalizeScript.onload = () => {
      const script = document.createElement('script');
      script.id = 'xne-injected-script';
      script.src = chrome.runtime.getURL('src/injected.js');
      (document.head || document.documentElement).appendChild(script);
      console.log('[XNE Content] Page scripts injected.');
    };
  }
  
  // Auto-scroll on profile pages to trigger the request that background.js captures
  function autoScrollIfNeeded() {
    const url = window.location.href;
    const profileMatch = url.match(/^https:\/\/x\.com\/([^\/\?]+)(\/with_replies)?(\?.*)?$/);
    const excludedPaths = ['home', 'explore', 'notifications', 'messages', 'i', 'settings', 'search', 'compose'];
    
    if (profileMatch && !excludedPaths.includes(profileMatch[1])) {
      console.log('[XNE Content] On profile page, scrolling to trigger request...');
      
      let scrollCount = 0;
      const scrollInterval = setInterval(() => {
        scrollCount++;
        window.scrollBy(0, 400);
        console.log('[XNE Content] Scroll', scrollCount);
        
        if (scrollCount >= 4) {
          clearInterval(scrollInterval);
          setTimeout(() => {
            window.scrollTo(0, 0);
            console.log('[XNE Content] Scroll complete.');
          }, 1000);
        }
      }, 400);
    }
  }
  
  // Initialize
  function init() {
    injectPageScripts();
    setTimeout(autoScrollIfNeeded, 1500);
  }
  
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
  
  // Handle messages from popup
  chrome.runtime.onMessage.addListener(async (message, sender, sendResponse) => {
    console.log('[XNE Content] Message from popup:', message.type);
    
    if (message.type === 'XNE_START') {
      // Get captured template from storage and include it
      try {
        const stored = await chrome.storage.local.get(['capturedTemplate']);
        const payload = {
          ...message.payload,
          capturedTemplate: stored.capturedTemplate || null
        };
        
        console.log('[XNE Content] Forwarding START with template:', !!stored.capturedTemplate);
        
        window.postMessage({
          type: 'XNE_START',
          payload: payload,
          source: 'xne-content'
        }, '*');
      } catch (err) {
        console.error('[XNE Content] Failed to get template:', err);
        window.postMessage({
          type: message.type,
          payload: message.payload,
          source: 'xne-content'
        }, '*');
      }
    } else {
      // Forward other messages directly
      window.postMessage({
        type: message.type,
        payload: message.payload,
        source: 'xne-content'
      }, '*');
    }
    
    sendResponse({ received: true });
    return true;
  });
  
  // Forward messages from injected.js to popup/background
  window.addEventListener('message', (event) => {
    if (event.source !== window) return;
    if (!event.data || event.data.source !== 'xne-injected') return;
    
    try {
      chrome.runtime.sendMessage({ 
        type: event.data.type, 
        payload: event.data.payload 
      });
    } catch (err) {
      // Popup closed
    }
  });
  
  console.log('[XNE Content] Setup complete.');
})();
