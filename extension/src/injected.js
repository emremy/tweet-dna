/**
 * Injected script for X Network Exporter
 * Runs in page context to make authenticated GraphQL requests
 */

(function () {
  'use strict';

  if (window.__XNE_INJECTED__) {
    console.log('[XNE Injected] Already injected, skipping.');
    return;
  }
  window.__XNE_INJECTED__ = true;

  console.log('[XNE Injected] Script loaded in page context.');

  // State
  let running = false;
  let tweets = [];
  let seenTweetIds = new Set();
  let seenCursors = new Set();
  let pageCount = 0;

  // Get normalize functions
  const normalize = window.__XNE_NORMALIZE__;
  if (!normalize) {
    console.error('[XNE Injected] Normalize module not found!');
    return;
  }

  function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
  }

  function sendMessage(type, payload) {
    window.postMessage({
      type,
      payload,
      source: 'xne-injected'
    }, '*');
  }

  function deepClone(obj) {
    return JSON.parse(JSON.stringify(obj));
  }

  /**
   * Build request from captured template
   */
  function buildRequest(template, { userId, cursor, count }) {
    const cloned = deepClone(template);

    // Update variables
    let variables = cloned.variables || {};
    if (userId) {
      variables.userId = userId;
    }
    if (cursor) {
      variables.cursor = cursor;
    } else {
      delete variables.cursor;
    }
    if (count) {
      variables.count = count;
    }

    // Use captured headers (includes auth!)
    const headers = cloned.headers || {};

    // Build URL with query params (GET request)
    const baseUrl = cloned.baseUrl || cloned.url;
    const urlObj = new URL(baseUrl);

    urlObj.searchParams.set('variables', JSON.stringify(variables));

    if (cloned.features) {
      urlObj.searchParams.set('features', JSON.stringify(cloned.features));
    }

    if (cloned.fieldToggles) {
      urlObj.searchParams.set('fieldToggles', JSON.stringify(cloned.fieldToggles));
    }

    const init = {
      method: 'GET',
      headers: headers,
      credentials: 'include',
      mode: 'cors'
    };

    return { url: urlObj.toString(), init };
  }

  /**
   * Run the export process
   */
  async function runExport(config) {
    if (running) {
      console.log('[XNE Injected] Already running.');
      return;
    }

    // Get template from config (passed from content script which got it from storage)
    const template = config.template || config.capturedTemplate;

    if (!template) {
      sendMessage('XNE_ERROR', {
        message: 'No request template available. Click "Capture" to capture a request first.'
      });
      return;
    }

    console.log('[XNE Injected] Starting export...');
    console.log('[XNE Injected] Template baseUrl:', template.baseUrl);
    console.log('[XNE Injected] Template has headers:', Object.keys(template.headers || {}).length);
    console.log('[XNE Injected] Target userId:', config.targetUserId);
    console.log('[XNE Injected] Min views filter:', config.minViews || 'disabled');

    // Initialize state
    running = true;
    tweets = [];
    seenTweetIds = new Set();
    seenCursors = new Set();
    pageCount = 0;

    let cursor = null;

    try {
      while (running && tweets.length < config.maxTweets) {
        const { url, init } = buildRequest(template, {
          userId: config.targetUserId,
          cursor: cursor,
          count: 20
        });

        console.log('[XNE Injected] Fetching page', pageCount + 1);

        const response = await fetch(url, init);

        // Handle 404 as "end of timeline" - not an error
        if (response.status === 404) {
          console.log('[XNE Injected] Got 404 - reached end of timeline.');
          break;
        }

        // Handle rate limiting
        if (response.status === 429) {
          console.log('[XNE Injected] Rate limited. Waiting 60 seconds...');
          sendMessage('XNE_PROGRESS', {
            count: tweets.length,
            pages: pageCount,
            status: 'Rate limited, waiting...'
          });
          await sleep(60000);
          continue; // Retry the same page
        }

        if (!response.ok) {
          const errorText = await response.text();
          console.error('[XNE Injected] HTTP Error:', response.status, errorText.substring(0, 200));
          throw new Error(`HTTP ${response.status}: ${errorText.substring(0, 100)}`);
        }

        const json = await response.json();

        if (json.errors && json.errors.length > 0) {
          const errorMsg = json.errors.map(e => e.message).join(', ');
          throw new Error(`GraphQL errors: ${errorMsg}`);
        }

        const { items, nextCursor } = normalize.extractTweetsAndCursor(json);

        console.log('[XNE Injected] Found', items.length, 'tweets, next cursor:', nextCursor ? 'yes' : 'no');

        // Add username if not present
        for (const item of items) {
          if (!item.username && config.targetUsername) {
            item.username = config.targetUsername;
            item.permalink = `https://x.com/${config.targetUsername}/status/${item.id}`;
          }
        }

        // Dedupe, filter, and collect
        let newCount = 0;
        const minViews = config.minViews || 0;
        
        for (const tweet of items) {
          if (!seenTweetIds.has(tweet.id)) {
            seenTweetIds.add(tweet.id);
            
            // Filter by minimum views if specified
            if (minViews > 0) {
              const tweetViews = tweet.views || 0;
              if (tweetViews < minViews) {
                continue; // Skip tweets below minimum views
              }
            }
            
            tweets.push(tweet);
            newCount++;

            if (tweets.length >= config.maxTweets) {
              break;
            }
          }
        }

        pageCount++;

        sendMessage('XNE_PROGRESS', {
          count: tweets.length,
          pages: pageCount,
          newThisPage: newCount
        });

        if (!nextCursor) {
          console.log('[XNE Injected] No next cursor, stopping.');
          break;
        }

        if (seenCursors.has(nextCursor)) {
          console.log('[XNE Injected] Cursor already seen, stopping.');
          break;
        }

        seenCursors.add(nextCursor);
        cursor = nextCursor;

        await sleep(config.delayMs || 750);
      }

      console.log('[XNE Injected] Export complete. Total tweets:', tweets.length);

      running = false;
      sendMessage('XNE_DONE', { count: tweets.length, pages: pageCount });

    } catch (error) {
      console.error('[XNE Injected] Export error:', error);
      running = false;
      sendMessage('XNE_ERROR', {
        message: error.message || 'Unknown error occurred',
        pages: pageCount,
        count: tweets.length
      });
    }
  }

  function stopExport() {
    console.log('[XNE Injected] Stop requested.');
    running = false;
  }

  function getData() {
    console.log('[XNE Injected] Data requested. Sending', tweets.length, 'tweets.');
    sendMessage('XNE_DATA', { tweets: tweets });
  }

  function resetState() {
    console.log('[XNE Injected] Reset requested.');
    running = false;
    tweets = [];
    seenTweetIds = new Set();
    seenCursors = new Set();
    pageCount = 0;
  }

  // Listen for messages from content script
  window.addEventListener('message', (event) => {
    if (event.source !== window) return;
    if (!event.data || event.data.source !== 'xne-content') return;

    const { type, payload } = event.data;
    console.log('[XNE Injected] Received:', type);

    switch (type) {
      case 'XNE_START':
        runExport(payload);
        break;
      case 'XNE_STOP':
        stopExport();
        break;
      case 'XNE_GET_DATA':
        getData();
        break;
      case 'XNE_RESET':
        resetState();
        break;
    }
  });

  console.log('[XNE Injected] Ready.');
})();
