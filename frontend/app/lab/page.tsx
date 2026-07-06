"use client";

import React, { useState, useEffect } from "react";
import { Search, Activity, ShieldAlert, Zap, TrendingUp, Award } from "lucide-react";
import { 
  Radar, RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, 
  ResponsiveContainer, ComposedChart, Line, Bar, XAxis, YAxis, Tooltip, Legend 
} from "recharts";

// --- API SCHEMAS ---
interface DNAMetrics {
  batting_strike_rate: number;
  batting_average: number;
  boundary_percentage: number;
  economy_rate: number;
  bowling_strike_rate: number;
}

interface SeasonStat {
  year: number;
  matches: number;
  runs_scored: number;
  strike_rate: number;
  wickets: number;
  economy: number;
}

interface PlayerLabData {
  player_name: string;
  dna: DNAMetrics;
  career_timeline: SeasonStat[];
}

export default function PlayerLabPage() {
  const [searchInput, setSearchInput] = useState("");
  const [activeQuery, setActiveQuery] = useState("");
  const [playerData, setPlayerData] = useState<PlayerLabData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [timelineMode, setTimelineMode] = useState<"batting" | "bowling">("batting");

  useEffect(() => {
    if (!activeQuery) return;
    setLoading(true);
    setError(null);

    fetch(`https://cricketops.onrender.com/api/v1/lab/player-lab/${encodeURIComponent(activeQuery)}`)
      .then((res) => {
        if (!res.ok) throw new Error(`No laboratory ledgers found for "${activeQuery}"`);
        return res.json();
      })
      .then((data) => {
        setPlayerData(data);
        // Smart default: If they take way more wickets than runs, open in bowling view
        const totalWickets = data.career_timeline.reduce((acc: number, curr: SeasonStat) => acc + curr.wickets, 0);
        if (totalWickets > 30) setTimelineMode("bowling");
        else setTimelineMode("batting");
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [activeQuery]);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (searchInput.trim()) setActiveQuery(searchInput.trim());
  };

  // --- SCALE NORMALIZER FOR THE 360° DNA RADAR ---
  const getNormalizedRadar = (dna: DNAMetrics) => {
    return [
      {
        metric: "Batting SR",
        realValue: `${dna.batting_strike_rate}`,
        // SR 100 -> 0%, SR 175 -> 100%
        score: Math.min(100, Math.max(0, ((dna.batting_strike_rate - 100) / 75) * 100))
      },
      {
        metric: "Batting Avg",
        realValue: `${dna.batting_average}`,
        // Avg 15 -> 0%, Avg 45 -> 100%
        score: Math.min(100, Math.max(0, ((dna.batting_average - 15) / 30) * 100))
      },
      {
        metric: "Boundary %",
        realValue: `${dna.boundary_percentage}%`,
        // 10% -> 0%, 25% -> 100%
        score: Math.min(100, Math.max(0, ((dna.boundary_percentage - 10) / 15) * 100))
      },
      {
        metric: "Economy Rate",
        realValue: `${dna.economy_rate}`,
        // INVERTED: Econ 10.5 -> 0%, Econ 6.0 -> 100%
        score: Math.min(100, Math.max(0, ((10.5 - dna.economy_rate) / 4.5) * 100))
      },
      {
        metric: "Bowling SR",
        realValue: `${dna.bowling_strike_rate}`,
        // INVERTED: Wicket every 30 balls -> 0%, Wicket every 14 balls -> 100%
        score: Math.min(100, Math.max(0, ((30 - dna.bowling_strike_rate) / 16) * 100))
      }
    ];
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 p-6 md:p-10">
      
      {/* TOP BAR & SEARCH */}
      <div className="max-w-7xl mx-auto mb-8 flex flex-col md:flex-row items-start md:items-center justify-between gap-4 border-b border-slate-800 pb-6">
        <div>
          <h1 className="text-3xl font-black tracking-tight flex items-center gap-2">
            <Zap className="text-blue-500" />
            <span>The Player Analytics Lab</span>
          </h1>
          <p className="text-xs text-slate-400 mt-1">Multi-dimensional shape parsing & year-by-year trajectory streams</p>
        </div>

        <form onSubmit={handleSearch} className="flex items-center w-full md:w-80 bg-slate-900 border border-slate-700 rounded-xl overflow-hidden focus-within:border-blue-500 transition-colors shadow-inner">
          <input 
            type="text" 
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
            placeholder="Search roster ledger..." 
            className="w-full bg-transparent px-4 py-2.5 text-sm text-white focus:outline-none"
          />
          <button type="submit" className="px-3 text-slate-400 hover:text-white transition-colors">
            <Search className="w-4 h-4" />
          </button>
        </form>
      </div>

      {/* ERROR STATE */}
      {error && (
        <div className="max-w-7xl mx-auto mb-6 p-4 bg-red-950/40 border border-red-800/80 rounded-xl text-red-300 flex items-center gap-3">
          <ShieldAlert className="w-5 h-5 flex-shrink-0" />
          <span className="text-sm">{error}</span>
        </div>
      )}

      {/* LOADING STATE */}
      {loading && (
        <div className="max-w-7xl mx-auto py-32 flex flex-col items-center justify-center gap-3 text-slate-400">
          <Activity className="w-8 h-8 animate-spin text-blue-500" />
          <p className="text-sm animate-pulse">Running dual-source PostgreSQL/CSV aggregation...</p>
        </div>
      )}

      {/* MAIN DASHBOARD */}
      {playerData && !loading && (
        <div className="max-w-7xl mx-auto grid grid-cols-1 lg:grid-cols-12 gap-8">
          
          {/* LEFT: 360° DNA SUPERNOVA (5 Cols) */}
          <div className="lg:col-span-5 bg-slate-900/60 border border-slate-800/80 rounded-2xl p-6 flex flex-col justify-between shadow-xl">
            <div>
              <div className="flex items-center justify-between border-b border-slate-800 pb-4 mb-4">
                <div>
                  <span className="text-xs font-bold uppercase tracking-widest text-blue-400">Static DNA Fingerprint</span>
                  <h2 className="text-2xl font-black text-white">{playerData.player_name}</h2>
                </div>
                <Award className="text-slate-600 w-6 h-6" />
              </div>

              <div className="h-[320px] w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <RadarChart cx="50%" cy="50%" outerRadius="75%" data={getNormalizedRadar(playerData.dna)}>
                    <PolarGrid stroke="#334155" />
                    <PolarAngleAxis dataKey="metric" tick={{ fill: "#94a3b8", fontSize: 11 }} />
                    <PolarRadiusAxis angle={30} domain={[0, 100]} axisLine={false} tick={false} />
                    <Radar name="Archetype" dataKey="score" stroke="#3b82f6" fill="#3b82f6" fillOpacity={0.45} />
                    
                    <Tooltip 
                      content={({ active, payload }) => {
                        if (active && payload && payload.length) {
                          const data = payload[0].payload;
                          return (
                            <div className="bg-slate-950 border border-slate-700 px-3 py-1.5 rounded-lg text-xs shadow-lg">
                              <span className="text-slate-400 font-medium">{data.metric}: </span>
                              <span className="text-blue-400 font-bold">{data.realValue}</span>
                            </div>
                          );
                        }
                        return null;
                      }} 
                    />
                  </RadarChart>
                </ResponsiveContainer>
              </div>
            </div>

            {/* RAW READOUT PILLS */}
            <div className="grid grid-cols-3 gap-2 pt-4 border-t border-slate-800">
              <div className="bg-slate-950/60 p-2.5 rounded-xl border border-slate-800/60 text-center">
                <div className="text-[10px] text-slate-400 uppercase">Batting SR</div>
                <div className="text-sm font-bold text-slate-200">{playerData.dna.batting_strike_rate}</div>
              </div>
              <div className="bg-slate-950/60 p-2.5 rounded-xl border border-slate-800/60 text-center">
                <div className="text-[10px] text-slate-400 uppercase">Boundary %</div>
                <div className="text-sm font-bold text-slate-200">{playerData.dna.boundary_percentage}%</div>
              </div>
              <div className="bg-slate-950/60 p-2.5 rounded-xl border border-slate-800/60 text-center">
                <div className="text-[10px] text-slate-400 uppercase">Economy</div>
                <div className="text-sm font-bold text-slate-200">{playerData.dna.economy_rate}</div>
              </div>
            </div>
          </div>

          {/* RIGHT: TIMELINE TRAJECTORY STREAM (7 Cols) */}
          <div className="lg:col-span-7 bg-slate-900/60 border border-slate-800/80 rounded-2xl p-6 flex flex-col justify-between shadow-xl">
            
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-800 pb-4 mb-6">
              <div>
                <span className="text-xs font-bold uppercase tracking-widest text-purple-400">Multi-Year Trajectory Stream</span>
                <h3 className="text-lg font-bold text-white">Seasonal Output (2018 – 2025)</h3>
              </div>

              {/* VIEW TOGGLE */}
              <div className="flex bg-slate-950 p-1 rounded-xl border border-slate-800">
                <button
                  onClick={() => setTimelineMode("batting")}
                  className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all ${
                    timelineMode === "batting" ? "bg-blue-600 text-white" : "text-slate-400 hover:text-white"
                  }`}
                >
                  Batting Volume
                </button>
                <button
                  onClick={() => setTimelineMode("bowling")}
                  className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all ${
                    timelineMode === "bowling" ? "bg-purple-600 text-white" : "text-slate-400 hover:text-white"
                  }`}
                >
                  Bowling Pressure
                </button>
              </div>
            </div>

            {/* COMPOSED CHART */}
            <div className="h-[340px] w-full">
              <ResponsiveContainer width="100%" height="100%">
                <ComposedChart data={playerData.career_timeline}>
                  <XAxis dataKey="year" stroke="#64748b" fontSize={12} tickLine={false} />
                  
                  {/* Left Y-Axis: Volume (Runs/Wickets) */}
                  <YAxis yAxisId="left" stroke="#64748b" fontSize={11} tickLine={false} orientation="left" />
                  
                  {/* Right Y-Axis: Efficiency (SR/Econ) */}
                  <YAxis yAxisId="right" stroke="#64748b" fontSize={11} tickLine={false} orientation="right" domain={[0, 'auto']} />
                  
                  <Tooltip 
                    contentStyle={{ backgroundColor: "#020617", borderColor: "#334155", borderRadius: "12px", fontSize: "12px" }}
                    labelStyle={{ color: "#38bdf8", fontWeight: "bold", marginBottom: "4px" }}
                  />
                  <Legend wrapperStyle={{ fontSize: "11px", paddingTop: "10px" }} />

                  {timelineMode === "batting" ? (
                    <>
                      <Bar yAxisId="left" name="Runs Scored" dataKey="runs_scored" fill="#0ea5e9" radius={[4, 4, 0, 0]} />
                      <Line yAxisId="right" name="Strike Rate" type="monotone" dataKey="strike_rate" stroke="#a855f7" strokeWidth={2.5} dot={{ r: 4, fill: "#a855f7" }} />
                    </>
                  ) : (
                    <>
                      <Bar yAxisId="left" name="Wickets Taken" dataKey="wickets" fill="#8b5cf6" radius={[4, 4, 0, 0]} />
                      <Line yAxisId="right" name="Economy Rate" type="monotone" dataKey="economy" stroke="#ec4899" strokeWidth={2.5} dot={{ r: 4, fill: "#ec4899" }} />
                    </>
                  )}
                </ComposedChart>
              </ResponsiveContainer>
            </div>

            <div className="mt-4 pt-4 border-t border-slate-800 text-center">
              <span className="text-xs text-slate-500">
                Data rendered directly from server-side pandas aggregation of <code className="text-slate-400">stats.csv</code>
              </span>
            </div>

          </div>

        </div>
      )}

    </div>
  );
}