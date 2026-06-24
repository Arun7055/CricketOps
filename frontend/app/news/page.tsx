"use client";

import React, { useState, useEffect } from "react";
import { 
  Newspaper, Radio, Search, ShieldAlert, 
  MapPin, Clock, Tag, Flame
} from "lucide-react";

interface NewsArticle {
  id: string;
  title: string;
  summary: string;
  category: "domestic" | "international";
  source_wire: string;
  published_time: string;
  impact_level: "Critical" | "High Impact" | "Medium Impact";
  tags: string[];
}

export default function IntelligenceWirePage() {
  const [articles, setArticles] = useState<NewsArticle[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // --- FILTER & SEARCH STATE ---
  const [activeTab, setActiveTab] = useState<"all" | "domestic" | "international">("all");
  const [searchQuery, setSearchQuery] = useState("");

  useEffect(() => {
    fetch("http://127.0.0.1:8000/api/v1/news/feed")
      .then(async (res) => {
        const payload = await res.json();
        if (!res.ok) throw new Error(payload.detail || "Failed to pull intelligence wire.");
        return payload;
      })
      .then((data) => {
        setArticles(data);
        setLoading(false);
      })
      .catch((err) => {
        setError(err.message);
        setLoading(false);
      });
  }, []);

  // Instant Client-Side Slicing
  const filteredArticles = articles.filter((item) => {
    const matchesTab = activeTab === "all" || item.category === activeTab;
    const matchesSearch = 
      item.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      item.summary.toLowerCase().includes(searchQuery.toLowerCase()) ||
      item.tags.some((t) => t.toLowerCase().includes(searchQuery.toLowerCase()));

    return matchesTab && matchesSearch;
  });

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 p-6 md:p-10">
      
      {/* HEADER COCKPIT */}
      <div className="max-w-6xl mx-auto border-b border-slate-800 pb-6 mb-8 flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-black tracking-tight text-white flex items-center gap-2.5">
            <Radio className="text-emerald-500 animate-pulse" />
            <span>Sub-Surface Intelligence Wire</span>
          </h1>
          <p className="text-xs text-slate-400 mt-1">Real-time domestic scout telemetry and global ballistics chatter</p>
        </div>

        {/* SEARCH BAR */}
        <div className="relative w-full md:w-72">
          <Search className="absolute left-3 top-2.5 w-4 h-4 text-slate-500" />
          <input 
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Filter keywords, tags..."
            className="w-full bg-slate-900/90 border border-slate-800 rounded-xl pl-9 pr-4 py-2 text-xs text-white placeholder-slate-500 outline-none focus:border-emerald-500 transition-all"
          />
        </div>
      </div>

      {error && (
        <div className="max-w-6xl mx-auto mb-6 p-4 bg-red-950/40 border border-red-800 rounded-xl text-red-300 text-xs flex items-center gap-2">
          <ShieldAlert className="w-4 h-4 flex-shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* THE TOGGLE TABS */}
      <div className="max-w-6xl mx-auto mb-8 flex items-center gap-2 bg-slate-900/60 p-1.5 rounded-xl border border-slate-800/80 w-fit">
        <button
          onClick={() => setActiveTab("all")}
          className={`px-5 py-2 rounded-lg text-xs font-black uppercase tracking-wider transition-all ${
            activeTab === "all" ? "bg-emerald-600 text-white shadow-lg shadow-emerald-600/20" : "text-slate-400 hover:text-white"
          }`}
        >
          All Vectors ({articles.length})
        </button>

        <button
          onClick={() => setActiveTab("domestic")}
          className={`px-5 py-2 rounded-lg text-xs font-black uppercase tracking-wider transition-all flex items-center gap-1.5 ${
            activeTab === "domestic" ? "bg-purple-600 text-white shadow-lg shadow-purple-600/20" : "text-slate-400 hover:text-white"
          }`}
        >
          <span className="w-2 h-2 rounded-full bg-purple-400"></span>
          Domestic Scouts ({articles.filter(a => a.category === "domestic").length})
        </button>

        <button
          onClick={() => setActiveTab("international")}
          className={`px-5 py-2 rounded-lg text-xs font-black uppercase tracking-wider transition-all flex items-center gap-1.5 ${
            activeTab === "international" ? "bg-blue-600 text-white shadow-lg shadow-blue-600/20" : "text-slate-400 hover:text-white"
          }`}
        >
          <span className="w-2 h-2 rounded-full bg-blue-400"></span>
          International ({articles.filter(a => a.category === "international").length})
        </button>
      </div>

      {/* NEWS MASONRY / GRID */}
      <div className="max-w-6xl mx-auto grid grid-cols-1 md:grid-cols-2 gap-6">
        
        {loading && (
          <div className="col-span-2 py-24 flex flex-col items-center justify-center text-slate-600 text-xs">
            <Radio className="w-8 h-8 animate-spin text-slate-700 mb-2" />
            <span>Tapping into regional cricket tele-printers...</span>
          </div>
        )}

        {!loading && filteredArticles.length === 0 && (
          <div className="col-span-2 py-20 border border-dashed border-slate-800 rounded-2xl text-center text-slate-500 text-xs">
            No intelligence transmissions match your active criteria.
          </div>
        )}

        {!loading && filteredArticles.map((item) => {
          const isDomestic = item.category === "domestic";
          const isCritical = item.impact_level === "Critical";

          return (
            <div 
              key={item.id}
              className="bg-slate-900/40 border border-slate-800/80 rounded-2xl p-6 hover:border-slate-700 transition-all flex flex-col justify-between group"
            >
              <div>
                {/* TOP METADATA ROW */}
                <div className="flex items-center justify-between gap-2 mb-3">
                  <div className="flex items-center gap-2">
                    <span className={`px-2.5 py-0.5 rounded-full text-[10px] font-black uppercase tracking-wider ${
                      isDomestic ? "bg-purple-500/10 text-purple-400 border border-purple-500/20" : "bg-blue-500/10 text-blue-400 border border-blue-500/20"
                    }`}>
                      {isDomestic ? "Domestic Scout" : "ICC Wire"}
                    </span>

                    <span className="text-slate-500 text-[11px] flex items-center gap-1">
                      <Clock className="w-3 h-3" /> {item.published_time}
                    </span>
                  </div>

                  {/* IMPACT BADGE */}
                  <span className={`px-2 py-0.5 rounded text-[10px] font-black uppercase flex items-center gap-1 ${
                    isCritical ? "bg-red-500/20 text-red-400 border border-red-500/30" : "bg-amber-500/10 text-amber-400"
                  }`}>
                    {isCritical && <Flame className="w-3 h-3 text-red-500 animate-bounce" />}
                    {item.impact_level}
                  </span>
                </div>

                {/* TITLE & SUMMARY */}
                <h3 className="text-base font-bold text-white group-hover:text-emerald-400 transition-colors leading-snug mb-2">
                  {item.title}
                </h3>

                <p className="text-slate-400 text-xs leading-relaxed mb-6">
                  {item.summary}
                </p>
              </div>

              {/* FOOTER: SOURCE & TAGS */}
              <div className="border-t border-slate-800/60 pt-4 flex items-center justify-between gap-2 flex-wrap">
                <span className="text-[11px] font-bold text-slate-300 flex items-center gap-1">
                  <MapPin className="w-3 h-3 text-emerald-500" />
                  {item.source_wire}
                </span>

                <div className="flex items-center gap-1.5 flex-wrap">
                  {item.tags.map((tag, tIdx) => (
                    <span key={tIdx} className="bg-slate-950 text-slate-400 hover:text-slate-200 px-2 py-0.5 rounded-md text-[10px] font-medium transition-colors">
                      #{tag}
                    </span>
                  ))}
                </div>
              </div>

            </div>
          );
        })}

      </div>

    </div>
  );
}