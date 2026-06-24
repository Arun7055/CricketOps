"use client";

import React, { useState, useEffect } from "react";
import { 
  Users, ShieldAlert, Activity, ShieldCheck, 
  CloudRain, Target, Swords
} from "lucide-react";

interface MatchupDetail {
  user_player: string;
  opposition_player: string;
  advantage: "Favorable" | "Danger";
  tactical_rationale: string;
}

interface PhaseItem {
  phase_label: string;
  tactical_script: string;
}

interface StrategyResponse {
  overall_win_condition: string;
  batting_phases: PhaseItem[];  // Changed
  bowling_phases: PhaseItem[];  // Changed
  key_matchups: MatchupDetail[];
}

export default function TacticalWarRoomPage() {
  const [allPlayers, setAllPlayers] = useState<{ id: string; name: string; role: string }[]>([]);
  
  // --- FORM STATE ---
  const [userXi, setUserXi] = useState<string[]>(Array(11).fill(""));
  const [oppositionXi, setOppositionXi] = useState<string[]>(Array(11).fill(""));
  const [venue, setVenue] = useState("Wankhede Stadium, Mumbai"); // Back to custom text!
  const [format, setFormat] = useState("T20");
  const [innings, setInnings] = useState("Batting 1st");
  const [pitchType, setPitchType] = useState("Hard");
  const [weather, setWeather] = useState("Sunny");
  const [timeOfPlay, setTimeOfPlay] = useState("Night");

  const [strategyResult, setStrategyResult] = useState<StrategyResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // 1. Safe Player Fetcher
  useEffect(() => {
    fetch("http://127.0.0.1:8000/api/v1/team/players")
      .then(async (res) => {
        const payload = await res.json();
        if (!res.ok) throw new Error(payload.detail || "HTTP Error");
        return payload;
      })
      .then((data) => {
        if (Array.isArray(data)) setAllPlayers(data);
        else setAllPlayers([]);
      })
      .catch((err) => {
        setError(`Database unreachable: ${err.message}`);
        setAllPlayers([]);
      });
  }, []);

  const handlePlayerChange = (index: number, name: string, type: "user" | "opp") => {
    if (type === "user") {
      const updated = [...userXi];
      updated[index] = name;
      setUserXi(updated);
    } else {
      const updated = [...oppositionXi];
      updated[index] = name;
      setOppositionXi(updated);
    }
  };

  // --- 2. THE REAL-TIME COLLISION DETECTOR ---
  const isPlayerAlreadyPicked = (targetName: string, currentSquad: "user" | "opp", slotIndex: number) => {
    if (!targetName) return false;

    if (currentSquad === "user") {
      // Checked against User XI (excluding the slot we are currently sitting on)
      const inUser = userXi.some((name, idx) => idx !== slotIndex && name === targetName);
      // Checked against the entire Opposition XI
      const inOpp = oppositionXi.includes(targetName);
      return inUser || inOpp;
    } else {
      const inOpp = oppositionXi.some((name, idx) => idx !== slotIndex && name === targetName);
      const inUser = userXi.includes(targetName);
      return inOpp || inUser;
    }
  };

  const runWarRoomAnalysis = async () => {
    setLoading(true);
    setError(null);

    const filteredUser = userXi.filter(Boolean);
    const filteredOpp = oppositionXi.filter(Boolean);

    if (filteredUser.length !== 11 || filteredOpp.length !== 11) {
      setError("Roster Imbalance: You must assign a player to all 11 slots for both teams.");
      setLoading(false);
      return;
    }

    try {
      const response = await fetch("http://127.0.0.1:8000/api/v1/team/war-room-strategy", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          user_xi: filteredUser,
          opposition_xi: filteredOpp,
          venue: venue.trim() || "Neutral Venue",
          format,
          innings,
          pitch_type: pitchType,
          weather,
          wind_condition: "Calm", 
          time_of_play: timeOfPlay,
        }),
      });

      if (!response.ok) throw new Error("The AI Tactical Engine failed to compile this scenario.");
      const data = await response.json();
      setStrategyResult(data);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 p-6 md:p-10">
      
      <div className="max-w-7xl mx-auto border-b border-slate-800 pb-6 mb-8 flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-black tracking-tight text-white flex items-center gap-2">
            <Swords className="text-blue-500" />
            <span>The Tactical War Room</span>
          </h1>
          <p className="text-xs text-slate-400 mt-1">Simulate pitch physics, weather shifts, and 1v1 matchup advantages</p>
        </div>
      </div>

      {error && (
        <div className="max-w-7xl mx-auto mb-6 p-4 bg-red-950/40 border border-red-800/80 rounded-xl text-red-300 flex items-center gap-3 text-sm">
          <ShieldAlert className="w-5 h-5 flex-shrink-0" />
          <span>{error}</span>
        </div>
      )}

      <div className="max-w-7xl mx-auto grid grid-cols-1 lg:grid-cols-12 gap-8">
        
        {/* LEFT: ROSTER SELECTION & CLIMATE VECTORS (5 COLS) */}
        <div className="lg:col-span-5 space-y-6">
          <div className="bg-slate-900/50 border border-slate-800/80 rounded-2xl p-6 shadow-xl">
            
            <h2 className="text-md font-bold text-slate-200 uppercase tracking-wider mb-4 flex items-center gap-2">
              <Users className="w-4 h-4 text-blue-400" /> <span>Roster Assignment</span>
            </h2>

            <div className="grid grid-cols-2 gap-4">
              {/* USER SQUAD */}
              <div>
                <label className="text-xs text-blue-400 font-bold block mb-2">Your Playing XI</label>
                {userXi.map((val, idx) => (
                  <select 
                    key={`user-${idx}`} 
                    value={val} 
                    onChange={(e) => handlePlayerChange(idx, e.target.value, "user")}
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg p-1.5 text-xs text-white mb-1.5 focus:border-blue-500 outline-none"
                  >
                    <option value="">-- Slot {idx+1} --</option>
                    {(Array.isArray(allPlayers) ? allPlayers : []).map((p) => {
                      const isPicked = isPlayerAlreadyPicked(p.name, "user", idx);
                      return (
                        <option key={`u-opt-${p.id}`} value={p.name} disabled={isPicked}>
                          {p.name} {isPicked ? "(Picked)" : ""}
                        </option>
                      );
                    })}
                  </select>
                ))}
              </div>

              {/* OPPOSITION SQUAD */}
              <div>
                <label className="text-xs text-red-400 font-bold block mb-2">Opposition XI</label>
                {oppositionXi.map((val, idx) => (
                  <select 
                    key={`opp-${idx}`} 
                    value={val} 
                    onChange={(e) => handlePlayerChange(idx, e.target.value, "opp")}
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg p-1.5 text-xs text-white mb-1.5 focus:border-red-500 outline-none"
                  >
                    <option value="">-- Slot {idx+1} --</option>
                    {(Array.isArray(allPlayers) ? allPlayers : []).map((p) => {
                      const isPicked = isPlayerAlreadyPicked(p.name, "opp", idx);
                      return (
                        <option key={`o-opt-${p.id}`} value={p.name} disabled={isPicked}>
                          {p.name} {isPicked ? "(Picked)" : ""}
                        </option>
                      );
                    })}
                  </select>
                ))}
              </div>
            </div>

            {/* MATCH CONDITIONS */}
            <h2 className="text-md font-bold text-slate-200 uppercase tracking-wider mt-6 mb-4 flex items-center gap-2">
              <CloudRain className="w-4 h-4 text-emerald-400" /> <span>Logistics & Surface Vectors</span>
            </h2>

            <div className="grid grid-cols-2 gap-4 text-xs">
              
              {/* VENUE (TEXT INPUT) */}
              <div className="col-span-2">
                <label className="text-slate-400 block mb-1 font-medium">Match Ground / Dimensions</label>
                <input 
                  type="text" 
                  value={venue}
                  onChange={(e) => setVenue(e.target.value)}
                  placeholder="e.g. Lord's, London (Slope / Seam)"
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2.5 text-white outline-none focus:border-emerald-500 transition-colors"
                />
              </div>

              <div>
                <label className="text-slate-400 block mb-1 font-medium">Match Format</label>
                <select value={format} onChange={(e) => setFormat(e.target.value)} className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2 text-white outline-none">
                  <option value="T20">T20 (20 Overs)</option>
                  <option value="ODI">ODI (50 Overs)</option>
                  <option value="Test">Test Match (5 Days)</option>
                </select>
              </div>

              <div>
                <label className="text-slate-400 block mb-1 font-medium">Pitch Surface</label>
                <select value={pitchType} onChange={(e) => setPitchType(e.target.value)} className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2 text-white outline-none">
                  <option value="Hard">Hard / True Bounce</option>
                  <option value="Dry">Dry / Turning</option>
                  <option value="Damp">Damp / Variable</option>
                  <option value="Green/Grass">Green / Seaming</option>
                </select>
              </div>

              <div>
                <label className="text-slate-400 block mb-1 font-medium">Weather Matrix</label>
                <select value={weather} onChange={(e) => setWeather(e.target.value)} className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2 text-white outline-none">
                  <option value="Sunny">Clear Skies / Sunny</option>
                  <option value="Overcast">Heavy Overcast / Swing</option>
                </select>
              </div>

              <div>
                <label className="text-slate-400 block mb-1 font-medium">Atmospheric Time</label>
                <select value={timeOfPlay} onChange={(e) => setTimeOfPlay(e.target.value)} className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2 text-white outline-none">
                  <option value="Day">Day Match</option>
                  <option value="Day-Night">Day-Night (Twilight)</option>
                  <option value="Night">Night Match (Under Lights)</option>
                </select>
              </div>

              <div className="col-span-2">
                <label className="text-slate-400 block mb-1 font-medium">Innings Strategy</label>
                <select value={innings} onChange={(e) => setInnings(e.target.value)} className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2 text-white outline-none">
                  <option value="Batting 1st">Setting Target (Batting 1st)</option>
                  <option value="Chasing (Batting 2nd)">Chasing Target (Batting 2nd)</option>
                </select>
              </div>

            </div>

            <button 
              onClick={runWarRoomAnalysis}
              disabled={loading}
              className="w-full mt-6 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 disabled:opacity-50 text-white text-sm font-black uppercase tracking-wider py-3 rounded-xl transition-all shadow-lg flex items-center justify-center gap-2"
            >
              {loading ? (
                <>
                  <Activity className="w-4 h-4 animate-spin" />
                  <span>Synthesizing Game Blueprint...</span>
                </>
              ) : (
                <>
                  <Target className="w-4 h-4" />
                  <span>Execute Roster Stress-Test</span>
                </>
              )}
            </button>

          </div>
        </div>

        {/* RIGHT: TACTICAL PLAYBOOK OUTPUT (7 COLS) */}
        <div className="lg:col-span-7">
          {!strategyResult && !loading && (
            <div className="h-full border border-dashed border-slate-800 rounded-2xl flex flex-col items-center justify-center p-8 text-center text-slate-500 py-36">
              <Swords className="w-12 h-12 text-slate-700 mb-3" />
              <p className="text-sm font-medium">War Room Awaiting Configuration</p>
              <p className="text-xs text-slate-600 mt-1 max-w-xs">Lock in your 22 players and surface variables to generate a custom match playbook.</p>
            </div>
          )}

          {strategyResult && !loading && (
            <div className="space-y-6">
              
              {/* CORE WIN CONDITION */}
              <div className="bg-gradient-to-br from-slate-900 to-slate-950 border border-blue-900/40 p-6 rounded-2xl shadow-xl">
                <span className="text-[10px] uppercase font-black tracking-widest text-blue-400">Strategic Consensus</span>
                <h3 className="text-lg font-black text-white mt-1 mb-2">Core Win Condition</h3>
                <p className="text-sm text-slate-300 leading-relaxed border-l-2 border-blue-500 pl-4">{strategyResult.overall_win_condition}</p>
              </div>

              {/* BATTING & BOWLING PHASIC GRIDS */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                
                {/* DYNAMIC BATTING PLAYBOOK */}
                <div className="bg-slate-900/60 border border-slate-800/80 p-5 rounded-2xl">
                  <h4 className="text-xs uppercase font-black text-blue-400 tracking-wider border-b border-slate-800 pb-2 mb-3">Batting Phasic Playbook</h4>
                  <div className="space-y-3 text-xs">
                    {strategyResult.batting_phases.map((phase, idx) => (
                      <div key={`bat-p-${idx}`}>
                        <span className="text-slate-400 font-bold block">{phase.phase_label}:</span> 
                        <p className="text-slate-300 mt-0.5 leading-relaxed">{phase.tactical_script}</p>
                      </div>
                    ))}
                  </div>
                </div>

                {/* DYNAMIC BOWLING SCRIPTS */}
                <div className="bg-slate-900/60 border border-slate-800/80 p-5 rounded-2xl">
                  <h4 className="text-xs uppercase font-black text-purple-400 tracking-wider border-b border-slate-800 pb-2 mb-3">Bowling Matchup Scripts</h4>
                  <div className="space-y-3 text-xs">
                    {strategyResult.bowling_phases.map((phase, idx) => (
                      <div key={`bowl-p-${idx}`}>
                        <span className="text-slate-400 font-bold block">{phase.phase_label}:</span> 
                        <p className="text-slate-300 mt-0.5 leading-relaxed">{phase.tactical_script}</p>
                      </div>
                    ))}
                  </div>
                </div>

              </div>

              {/* 1v1 KRYPTONITE MATRIX */}
              <div className="bg-slate-900/40 border border-slate-800/80 p-6 rounded-2xl">
                <h3 className="text-sm font-black text-slate-200 uppercase tracking-widest mb-4">Critical 1v1 Vulnerability Matrix</h3>
                <div className="space-y-3">
                  {strategyResult.key_matchups.map((duel, idx) => {
                    const isFav = duel.advantage === "Favorable";
                    return (
                      <div key={idx} className={`p-4 border rounded-xl flex items-start gap-4 ${isFav ? "bg-emerald-950/20 border-emerald-900/50" : "bg-red-950/20 border-red-900/50"}`}>
                        <div className={`p-2 rounded-lg ${isFav ? "bg-emerald-500/10 text-emerald-400" : "bg-red-500/10 text-red-400"}`}>
                          {isFav ? <ShieldCheck className="w-5 h-5" /> : <ShieldAlert className="w-5 h-5" />}
                        </div>
                        <div className="text-xs w-full">
                          <div className="flex items-center gap-2 mb-1 flex-wrap">
                            <span className="font-bold text-white text-sm">{duel.user_player}</span>
                            <span className="text-slate-500">vs</span>
                            <span className="font-bold text-slate-300 text-sm">{duel.opposition_player}</span>
                            <span className={`px-2 py-0.5 rounded text-[10px] font-black uppercase tracking-wider ml-auto ${isFav ? "bg-emerald-500/20 text-emerald-400" : "bg-red-500/20 text-red-400"}`}>
                              {isFav ? "Target Mismatch" : "Critical Danger"}
                            </span>
                          </div>
                          <p className="text-slate-400 leading-relaxed mt-1 text-[11px]">{duel.tactical_rationale}</p>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>

            </div>
          )}
        </div>

      </div>
    </div>
  );
}