/* Busy Bun — the saves on this device (IndexedDB), for offline play.
   One key/value store "kv" in the database "busybun". Values are JSON text written by client_code/bun.py:
     "world"          the journey (every level) and the catalog, refreshed whenever the game is online
     "current"        who was playing last ({"acct", "me"}), so the game opens as them offline
     "acct:guest"     the guest's progress on this device
     "acct:u:<email>" one per account that played here: progress, the copy the server last confirmed, levels won
                      since (for the leaderboards) and the id of an unfinished sync
   Every call returns a promise (Python waits for it). If IndexedDB can't be used (some private windows) it falls
   back to localStorage under "bbs.<key>". */
(function () {
  'use strict';
  var DB = 'busybun', ST = 'kv', opening = null;

  function open() {
    if (opening) return opening;
    opening = new Promise(function (res, rej) {
      try {
        var r = indexedDB.open(DB, 1);
        r.onupgradeneeded = function () { r.result.createObjectStore(ST); };
        r.onsuccess = function () { res(r.result); };
        r.onerror = function () { rej(r.error); };
        r.onblocked = function () { rej(new Error('blocked')); };
      } catch (e) { rej(e); }
    });
    opening.catch(function () { opening = null; });
    return opening;
  }

  function run(mode, fn) {
    return open().then(function (db) {
      return new Promise(function (res, rej) {
        var t = db.transaction(ST, mode), q = fn(t.objectStore(ST)), out = null;
        if (q) q.onsuccess = function () { out = q.result === undefined ? null : q.result; };
        t.oncomplete = function () { res(out); };
        t.onerror = t.onabort = function () { rej(t.error); };
      });
    });
  }

  function ls(fn) { try { return fn(window.localStorage); } catch (e) { return null; } }

  window.BBStore = {
    get: function (key) {
      return run('readonly', function (s) { return s.get(key); })
        .catch(function () { return ls(function (l) { return l.getItem('bbs.' + key); }); });
    },
    set: function (key, text) {
      return run('readwrite', function (s) { return s.put(text, key); }).then(function () { return true; })
        .catch(function () { return !!ls(function (l) { l.setItem('bbs.' + key, text); return true; }); });
    },
    del: function (key) {
      return run('readwrite', function (s) { return s.delete(key); }).then(function () { return true; })
        .catch(function () { return !!ls(function (l) { l.removeItem('bbs.' + key); return true; }); });
    },
    keys: function () {
      return run('readonly', function (s) { return s.getAllKeys(); }).then(function (k) { return JSON.stringify(k || []); })
        .catch(function () { return '[]'; });
    }
  };

  // Ask the browser to keep these saves even when the phone is low on space (it may say no; nothing breaks).
  try { if (navigator.storage && navigator.storage.persist) navigator.storage.persist(); } catch (e) {}

  // Network changes: Python listens through BBStore.onNet (set by bun.py).
  function net(online) { try { if (window.BBStore.onNet) window.BBStore.onNet(online); } catch (e) {} }
  window.addEventListener('online', function () { net(true); });
  window.addEventListener('offline', function () { net(false); });
})();
