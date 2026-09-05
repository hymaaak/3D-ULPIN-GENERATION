import { useEffect, useRef, useState } from 'react';
import * as searchApi from '../api/search.js';
import { asList } from '../utils/constants.js';

// ULPIN / parcel search box with debounced queries against
// GET /api/v1/search/ulpin. Calls onSelect(result) when the user picks one.
export default function ParcelSearch({ onSelect, placeholder = 'Search by ULPIN, survey no. or village…' }) {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState([]);
  const [open, setOpen] = useState(false);
  const [searching, setSearching] = useState(false);
  const wrapRef = useRef(null);

  useEffect(() => {
    const q = query.trim();
    if (q.length < 3) {
      setResults([]);
      setSearching(false);
      return undefined;
    }
    setSearching(true);
    const timer = setTimeout(async () => {
      try {
        const data = await searchApi.searchUlpin({ q });
        setResults(asList(data).slice(0, 10));
        setOpen(true);
      } catch {
        setResults([]);
      } finally {
        setSearching(false);
      }
    }, 350);
    return () => clearTimeout(timer);
  }, [query]);

  useEffect(() => {
    const onClickOutside = (e) => {
      if (wrapRef.current && !wrapRef.current.contains(e.target)) setOpen(false);
    };
    document.addEventListener('mousedown', onClickOutside);
    return () => document.removeEventListener('mousedown', onClickOutside);
  }, []);

  const handleSelect = (item) => {
    setOpen(false);
    setQuery(item.ulpin || item.unit_ulpin || '');
    if (onSelect) onSelect(item);
  };

  return (
    <div ref={wrapRef} className="relative">
      <div className="flex items-center gap-2">
        <input
          type="text"
          className="input"
          placeholder={placeholder}
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onFocus={() => results.length && setOpen(true)}
        />
        {searching && <span className="text-xs text-slate-400">…</span>}
      </div>
      {open && results.length > 0 && (
        <ul className="absolute z-20 mt-1 w-full overflow-hidden rounded-md border border-slate-200 bg-white shadow-lg">
          {results.map((item, i) => {
            const ulpin = item.ulpin || item.unit_ulpin || '';
            const label = item.village_code || item.floor_label || item.unit_type || '';
            return (
              <li key={item.unit_id || item.parcel_id || i}>
                <button
                  type="button"
                  className="block w-full px-3 py-2 text-left text-sm hover:bg-brand-50"
                  onClick={() => handleSelect(item)}
                >
                  <span className="font-mono text-xs text-brand-700">{ulpin}</span>
                  {label && <span className="ml-2 text-xs text-slate-500">{label}</span>}
                  {item.status && (
                    <span className="ml-2 text-xs capitalize text-slate-400">{item.status}</span>
                  )}
                </button>
              </li>
            );
          })}
        </ul>
      )}
      {open && query.trim().length >= 3 && results.length === 0 && !searching && (
        <div className="absolute z-20 mt-1 w-full rounded-md border border-slate-200 bg-white px-3 py-2 text-xs text-slate-500 shadow-lg">
          No matches — try a full ULPIN like 3D-ULPIN-27-023-456789-0001…
        </div>
      )}
    </div>
  );
}
