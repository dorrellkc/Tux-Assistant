/**
 * Tux Assistant Connector - Background Script
 * 
 * Catches theme and extension install requests and sends them to
 * Tux Assistant for handling via native messaging.
 */

const NATIVE_HOST = "tux_assistant";

// Track if native host is available
let nativeHostAvailable = true;

/**
 * Send a message to Tux Assistant native host
 */
function sendToTuxAssistant(action, data) {
    if (!nativeHostAvailable) {
        console.log("[Tux Connector] Native host not available, skipping");
        return Promise.resolve(false);
    }
    
    return browser.runtime.sendNativeMessage(NATIVE_HOST, {
        action: action,
        ...data
    }).then(response => {
        console.log("[Tux Connector] Response from Tux Assistant:", response);
        return true;
    }).catch(error => {
        console.error("[Tux Connector] Native messaging error:", error);
        // Don't disable permanently - might be temporary
        return false;
    });
}

/**
 * Handle OCS (Open Collaboration Services) protocol links
 * Used by gnome-look.org, opendesktop.org, pling.com, etc.
 * Format: ocs://install?url=https://...&type=...&filename=...
 */
function handleOcsLink(url) {
    console.log("[Tux Connector] Caught OCS link:", url);
    
    try {
        // Parse the OCS URL
        const ocsUrl = new URL(url);
        const params = ocsUrl.searchParams;
        
        const downloadUrl = params.get('url');
        const contentType = params.get('type') || 'unknown';
        const filename = params.get('filename') || 'download';
        
        if (downloadUrl) {
            sendToTuxAssistant('install_ocs', {
                download_url: downloadUrl,
                content_type: contentType,
                filename: filename,
                original_url: url
            });
            return true;
        }
    } catch (e) {
        console.error("[Tux Connector] Error parsing OCS URL:", e);
    }
    return false;
}

/**
 * Handle GNOME Extensions installation
 * Catches requests to extensions.gnome.org install endpoint
 */
function handleGnomeExtension(url, details) {
    console.log("[Tux Connector] Caught GNOME Extension install:", url);
    
    try {
        const urlObj = new URL(url);
        
        // Extract extension UUID from the URL
        // Format: /extension-data/uuid@domain/vXX.shell-extension.zip
        // Or: /download-extension/uuid@domain.shell-extension.zip?version_tag=...
        const pathMatch = url.match(/\/(?:extension-data|download-extension)\/([^\/]+?)(?:\/|\.shell-extension\.zip)/);
        
        if (pathMatch) {
            const uuid = pathMatch[1];
            sendToTuxAssistant('install_gnome_extension', {
                uuid: uuid,
                download_url: url,
                original_url: details.originUrl || url
            });
            return true;
        }
    } catch (e) {
        console.error("[Tux Connector] Error parsing GNOME extension URL:", e);
    }
    return false;
}

/**
 * Intercept requests to catch install actions
 */
browser.webRequest.onBeforeRequest.addListener(
    function(details) {
        const url = details.url;
        
        // Handle OCS protocol (ocs://install?...)
        if (url.startsWith('ocs://')) {
            if (handleOcsLink(url)) {
                return { cancel: true };
            }
        }
        
        // Handle GNOME Extensions downloads
        if (url.includes('extensions.gnome.org') && 
            (url.includes('/extension-data/') || url.includes('/download-extension/'))) {
            if (handleGnomeExtension(url, details)) {
                return { cancel: true };
            }
        }
        
        // Handle direct theme/icon downloads from gnome-look.org
        if ((url.includes('gnome-look.org') || url.includes('pling.com') || url.includes('opendesktop.org')) &&
            url.includes('/download')) {
            console.log("[Tux Connector] Caught theme download:", url);
            sendToTuxAssistant('install_theme', {
                download_url: url,
                source: 'gnome-look'
            });
            // Don't cancel - let the download proceed, Tux will handle install
        }
        
        return {};
    },
    { urls: ["<all_urls>"] },
    ["blocking"]
);

/**
 * Listen for messages from content scripts or popup (future use)
 */
browser.runtime.onMessage.addListener((message, sender, sendResponse) => {
    if (message.action === 'install') {
        sendToTuxAssistant('install', message.data).then(success => {
            sendResponse({ success: success });
        });
        return true; // Keep channel open for async response
    }
});

/**
 * Handle extension install/update
 */
browser.runtime.onInstalled.addListener((details) => {
    console.log("[Tux Connector] Extension installed/updated:", details.reason);
    
    // Test native host connection
    sendToTuxAssistant('ping', {}).then(success => {
        if (success) {
            console.log("[Tux Connector] Native host connection successful");
        } else {
            console.warn("[Tux Connector] Native host not responding - install handling disabled");
            nativeHostAvailable = false;
        }
    });
});

console.log("[Tux Connector] Background script loaded");
