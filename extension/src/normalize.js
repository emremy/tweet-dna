/**
 * Normalization module for X Network Exporter
 * Converts raw X GraphQL tweet data to canonical schema
 */

(function() {
  'use strict';
  
  /**
   * Parse X's date format to ISO 8601
   * X uses format like: "Thu Oct 10 12:34:56 +0000 2024"
   * @param {string} dateStr - Raw date string from X
   * @returns {string} ISO 8601 formatted date or original string if parsing fails
   */
  function parseXDate(dateStr) {
    if (!dateStr) return null;
    
    try {
      const date = new Date(dateStr);
      if (!isNaN(date.getTime())) {
        return date.toISOString();
      }
    } catch (e) {
      // Fall through
    }
    
    // Return original string if parsing fails
    return dateStr;
  }
  
  /**
   * Safely get nested property value
   * @param {object} obj - Object to traverse
   * @param {string} path - Dot-separated path (e.g., 'legacy.full_text')
   * @param {*} defaultValue - Default value if path not found
   * @returns {*} Value at path or default
   */
  function getNestedValue(obj, path, defaultValue = null) {
    if (!obj || !path) return defaultValue;
    
    const parts = path.split('.');
    let current = obj;
    
    for (const part of parts) {
      if (current === null || current === undefined) {
        return defaultValue;
      }
      current = current[part];
    }
    
    return current !== undefined ? current : defaultValue;
  }
  
  /**
   * Extract text from tweet object
   * Tries multiple paths as X's schema varies
   * @param {object} tweet - Raw tweet object
   * @returns {string|null} Tweet text
   */
  function extractText(tweet) {
    // Try various paths where text might be
    const paths = [
      'legacy.full_text',
      'full_text',
      'text',
      'legacy.text',
      'note_tweet.note_tweet_results.result.text'
    ];
    
    for (const path of paths) {
      const text = getNestedValue(tweet, path);
      if (text && typeof text === 'string') {
        return text;
      }
    }
    
    return null;
  }
  
  /**
   * Extract username from tweet or user object
   * @param {object} tweet - Raw tweet object
   * @returns {string|null} Username (without @)
   */
  function extractUsername(tweet) {
    const paths = [
      'core.user_results.result.legacy.screen_name',
      'legacy.user_id_str', // fallback, not ideal
      'user.screen_name',
      'author.screen_name'
    ];
    
    for (const path of paths) {
      const username = getNestedValue(tweet, path);
      if (username && typeof username === 'string') {
        return username;
      }
    }
    
    return null;
  }
  
  /**
   * Normalize a raw tweet object to canonical schema
   * @param {object} raw - Raw tweet object from X GraphQL response
   * @param {boolean} includeRaw - Whether to include raw data in output
   * @returns {object|null} Normalized tweet or null if invalid
   */
  function normalizeTweet(raw, includeRaw = false) {
    if (!raw) return null;
    
    // Handle wrapped results
    const tweet = raw.tweet_results?.result || raw.result || raw;
    
    // Skip non-tweet entries (like cursor entries, promoted content)
    if (!tweet || tweet.__typename === 'TweetTombstone') {
      return null;
    }
    
    // Get tweet ID
    const id = tweet.rest_id || tweet.id_str || tweet.id;
    if (!id) return null;
    
    // Get legacy data (where most tweet info lives)
    const legacy = tweet.legacy || {};
    
    // Extract text
    const text = extractText(tweet);
    if (!text) return null; // Skip tweets without text
    
    // Extract username
    const username = extractUsername(tweet);
    
    // Extract raw metrics (may not always be available)
    const publicMetrics = legacy.public_metrics || tweet.public_metrics || {};
    const legacyMetrics = {
      likes: legacy.favorite_count ?? publicMetrics.like_count ?? null,
      retweets: legacy.retweet_count ?? publicMetrics.retweet_count ?? null,
      replies: legacy.reply_count ?? publicMetrics.reply_count ?? null
    };
    
    // Views might be in a different location
    const views = getNestedValue(tweet, 'views.count') || 
                  getNestedValue(tweet, 'ext_views.count') ||
                  null;
    
    // Detect tweet types
    const isReply = Boolean(legacy.in_reply_to_status_id_str || legacy.in_reply_to_user_id_str);
    const isQuote = Boolean(legacy.is_quote_status || legacy.quoted_status_id_str);
    
    // Detect retweet: either from API flag or text pattern
    const isRetweet = Boolean(
      legacy.retweeted_status_result || 
      tweet.retweeted_status_result ||
      (text && text.startsWith('RT @'))
    );
    
    // Detect if tweet starts with mention (but is not a retweet)
    // These are often replies or direct mentions
    const startsWithMention = !isRetweet && text && text.startsWith('@');
    
    // Build metrics object (Python expects nested metrics)
    const metrics = {
      likes: legacyMetrics.likes !== null ? parseInt(legacyMetrics.likes, 10) : null,
      retweets: legacyMetrics.retweets !== null ? parseInt(legacyMetrics.retweets, 10) : null,
      replies: legacyMetrics.replies !== null ? parseInt(legacyMetrics.replies, 10) : null,
      quotes: legacy.quote_count !== undefined ? parseInt(legacy.quote_count, 10) : null,
      views: views !== null ? parseInt(views, 10) : null
    };
    
    // Build URL (Python expects 'url' field)
    const url = username && id ? `https://x.com/${username}/status/${id}` : null;
    
    // Build normalized tweet (schema aligned with Python ExtensionTweet model)
    const normalized = {
      id: id,
      text: text,
      created_at: parseXDate(legacy.created_at || tweet.created_at),
      url: url,
      source: 'extension_network',
      metrics: metrics,
      is_retweet: isRetweet,
      is_reply: isReply,
      is_quote: isQuote,
      is_mention: startsWithMention,
      username: username,
      conversation_id: legacy.conversation_id_str || null,
      lang: legacy.lang || null,
      raw: includeRaw ? raw : null
    };
    
    return normalized;
  }
  
  /**
   * Recursively find all tweet-like objects in a response
   * @param {*} obj - Object to search
   * @param {Array} results - Array to collect results
   * @param {Set} seenIds - Set of already seen tweet IDs
   */
  function findTweetObjects(obj, results = [], seenIds = new Set()) {
    if (!obj || typeof obj !== 'object') return results;
    
    // Check if this looks like a tweet result
    if (obj.rest_id && (obj.legacy || obj.__typename === 'Tweet')) {
      const id = obj.rest_id;
      if (!seenIds.has(id)) {
        seenIds.add(id);
        results.push(obj);
      }
    }
    
    // Check for tweet_results wrapper
    if (obj.tweet_results?.result?.rest_id) {
      const id = obj.tweet_results.result.rest_id;
      if (!seenIds.has(id)) {
        seenIds.add(id);
        results.push(obj.tweet_results.result);
      }
    }
    
    // Recurse into arrays and objects
    if (Array.isArray(obj)) {
      for (const item of obj) {
        findTweetObjects(item, results, seenIds);
      }
    } else {
      for (const key of Object.keys(obj)) {
        // Skip certain keys that are unlikely to contain tweets
        if (key === 'raw' || key === 'card') continue;
        findTweetObjects(obj[key], results, seenIds);
      }
    }
    
    return results;
  }
  
  /**
   * Find cursor value in response
   * @param {object} response - GraphQL response
   * @param {string} cursorType - 'Bottom' or 'Top'
   * @returns {string|null} Cursor value
   */
  function findCursor(response, cursorType = 'Bottom') {
    const cursorPattern = `cursor-${cursorType.toLowerCase()}`;
    
    function search(obj) {
      if (!obj || typeof obj !== 'object') return null;
      
      // Check for cursor entry
      if (obj.entryId && typeof obj.entryId === 'string') {
        if (obj.entryId.toLowerCase().includes(cursorPattern)) {
          // Try various paths for cursor value
          const value = obj.content?.value ||
                       obj.content?.itemContent?.value ||
                       obj.value;
          if (value) return value;
        }
      }
      
      // Check for cursorType property
      if (obj.cursorType === cursorType && obj.value) {
        return obj.value;
      }
      
      // Recurse
      if (Array.isArray(obj)) {
        for (const item of obj) {
          const found = search(item);
          if (found) return found;
        }
      } else {
        for (const key of Object.keys(obj)) {
          const found = search(obj[key]);
          if (found) return found;
        }
      }
      
      return null;
    }
    
    return search(response);
  }
  
  /**
   * Extract tweets and cursor from a GraphQL response
   * @param {object} response - Raw GraphQL response
   * @param {boolean} includeRaw - Whether to include raw data
   * @returns {object} { items: Array, nextCursor: string|null }
   */
  function extractTweetsAndCursor(response, includeRaw = false) {
    // Find all tweet objects
    const rawTweets = findTweetObjects(response);
    
    // Normalize tweets
    const items = [];
    for (const raw of rawTweets) {
      const normalized = normalizeTweet(raw, includeRaw);
      if (normalized) {
        items.push(normalized);
      }
    }
    
    // Find next cursor
    const nextCursor = findCursor(response, 'Bottom');
    
    return { items, nextCursor };
  }
  
  // Export to global scope for use by injected.js
  window.__XNE_NORMALIZE__ = {
    normalizeTweet,
    findTweetObjects,
    findCursor,
    extractTweetsAndCursor,
    parseXDate,
    getNestedValue
  };
  
  console.log('[XNE Normalize] Module loaded.');
})();
