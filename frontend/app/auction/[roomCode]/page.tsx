"use client";

import React, { useEffect, useState, useRef } from "react";
import { useRouter, useParams } from "next/navigation";
import { Users, Gavel, History, Activity, AlertTriangle, ShieldCheck, FastForward } from "lucide-react";

export default function LiveAuctionArena() {
  const router = useRouter();
  const params = useParams();
  const roomCode = params.roomCode as string;

  // --- Session State ---
  const [session, setSession] = useState<{ lobbyId: string; participantId: string; username: string } | null>(null);
  
  // --- WebSocket & Auction State ---
  const socketRef = useRef<WebSocket | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [logs, setLogs] = useState<{ id: number; text: string; type: "system" | "bid" }[]>([]);
  
  // Real active player state from DB
  const [playerOnBlock, setPlayerOnBlock] = useState<{name: string, role: string, base_price: number} | null>(null);
  const [currentBid, setCurrentBid] = useState(0); 
  const [highestBidder, setHighestBidder] = useState<string>("None");
  const [myPurse, setMyPurse] = useState(10000); // 100 Cr
  const [timeLeft, setTimeLeft] = useState<number | null>(null);
  const [squadSize, setSquadSize] = useState(0);

  const [hasVoted, setHasVoted] = useState(false);
  const [voteCount, setVoteCount] = useState({ current: 0, required: 0 });

  const [competitors, setCompetitors] = useState([]);
  const [auctionStatus, setAuctionStatus] = useState("waiting");
  const [lobbyHostId, setLobbyHostId] = useState("");

  useEffect(() => {
    // If timer is null or zero, do absolutely nothing
    if (timeLeft === null || timeLeft <= 0) return;

    // setTimeout automatically cleans itself up and guarantees exact 1-second intervals
    const timerId = setTimeout(() => {
      setTimeLeft(timeLeft - 1);
    }, 1000);

    return () => clearTimeout(timerId);
  }, [timeLeft]);

  useEffect(() => {
    // 1. Authenticate the local browser session
    const lobbyId = sessionStorage.getItem("crick_lobby_id");
    const participantId = sessionStorage.getItem("crick_participant_id");
    const username = sessionStorage.getItem("crick_username");

    if (!lobbyId || !participantId || !username) {
      router.push("/auction"); // Kick unauthorized users back to the landing page
      return;
    }

    setSession({ lobbyId, participantId, username });

    // 2. Fetch Initial Lobby State (The active player)
    const fetchLobbyState = async () => {
      try {
        // We add a timestamp to the URL to force the browser to skip the cache!
        const res = await fetch(`https://cricketops.onrender.com/api/v1/auction/state/${lobbyId}?t=${Date.now()}`);
        if (res.ok) {
          const data = await res.json();
          if (data.status === "completed") {
            addLog("All players sold! Auction Over.", "system");
            return;
          }
          if (data.player) {
            setPlayerOnBlock(data.player);
            setCurrentBid(data.current_bid);
            setHighestBidder(data.highest_bidder_name);
            setTimeLeft(null); // Clear timer when a new player drops
            setCompetitors(data.competitors)
            setAuctionStatus(data.status || "waiting");
            setLobbyHostId(data.host_id);
          }
        }
      } catch (err) {
        console.error("Failed to fetch lobby state", err);
      }
    };
    
    fetchLobbyState();

    const fetchMyPurse = async () => {
      try {
        const res = await fetch(`https://cricketops.onrender.com/api/v1/auction/participant/${participantId}/purse?t=${Date.now()}`);
        if (res.ok) {
          const data = await res.json();
          setMyPurse(data.purse_remaining);
          setSquadSize(data.squad_size);
        }
      } catch (err) {
        console.error("Failed to fetch purse", err);
      }
    };
    fetchMyPurse();

    // 3. Open the real-time WebSocket connection
    const wsUrl = `wss://cricketops.onrender.com/api/v1/auction/ws/${lobbyId}/${participantId}`;
    const ws = new WebSocket(wsUrl);
    socketRef.current = ws;

    ws.onopen = () => setIsConnected(true);

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      
      // Handle different message types broadcasted by FastAPI
      if (data.type === "SYSTEM_MESSAGE") {
        addLog(data.message, "system");
      } else if (data.type === "AUCTION_UPDATE") {
        setCurrentBid(data.current_bid);
        setHighestBidder(data.highest_bidder_name);
        setTimeLeft(15);
        setHasVoted(false);
        setVoteCount({ current: 0, required: 0 });
        addLog(`${data.highest_bidder_name} holds the bid at ₹${data.current_bid}L!`, "bid");
      }else if (data.type === "VOTE_UPDATE") {
        setVoteCount({ current: data.current, required: data.required });
      }else if (data.type === "PLAYER_SOLD") {
        setTimeLeft(0);
        setHasVoted(false); 
        setVoteCount({ current: 0, required: 0 });
        
        addLog(data.message, "system");
        
        // --- FIXED: Use sessionStorage directly to avoid the React null crash! ---
        const myUsername = sessionStorage.getItem("crick_username");
        if (data.buyer === myUsername) {
           // If we won, immediately ask the DB for our new official balance!
           setTimeout(() => { fetchMyPurse(); }, 500); 
        }
        
        // Wait 3 seconds, then get the next player
        setTimeout(() => {
          fetchLobbyState();
        }, 3000);
      }else if (data.type === "AUCTION_COMPLETED") {
        addLog(data.message, "system");
        
        // Wait 2 seconds so they can read the message, then teleport them!
        setTimeout(() => {
          router.push(`/selection/${lobbyId}`);
        }, 2000);
      }else if (data.type === "AUCTION_STARTED") {
        setAuctionStatus("active");
        addLog(data.message, "system");
        fetchLobbyState(); // Refresh to get the first player on the block
      }
    };

    ws.onclose = () => setIsConnected(false);

    // 4. Cleanup on unmount
    return () => {
      ws.close();
    };
  }, [router]);

  const addLog = (text: string, type: "system" | "bid") => {
    setLogs((prev) => [{ id: Date.now(), text, type }, ...prev].slice(0, 50)); // Keep last 50 logs
  };

  const placeBid = () => {
    if (!socketRef.current || socketRef.current.readyState !== WebSocket.OPEN) return;
    
    // Increment the bid by 50 Lakhs. 
    // The backend RabbitMQ consumer will validate if this is legal!
    const nextBid = currentBid + 50; 
    
    socketRef.current.send(
      JSON.stringify({
        action: "PLACE_BID",
        amount: nextBid,
      })
    );
  };

  const voteForceSell = () => {
    if (!socketRef.current || socketRef.current.readyState !== WebSocket.OPEN) return;
    setHasVoted(true);
    socketRef.current.send(JSON.stringify({ action: "FORCE_SELL_VOTE" }));
  };

  const requestFinishAuction = () => {
    if (!socketRef.current || socketRef.current.readyState !== WebSocket.OPEN) return;
    socketRef.current.send(JSON.stringify({ action: "FINISH_AUCTION_CHECK" }));
  };

  const startAuction = () => {
    if (!socketRef.current || socketRef.current.readyState !== WebSocket.OPEN) return;
    socketRef.current.send(JSON.stringify({ action: "START_AUCTION" }));
  };

  if (!session) return null; // Prevent flash of UI before redirect

  if (auctionStatus === "waiting") {
    return (
      <div className="min-h-screen bg-slate-950 flex flex-col items-center justify-center p-4 text-white">
        <div className="max-w-2xl w-full bg-slate-900 border border-slate-800 rounded-3xl p-8 shadow-2xl text-center">
          <h1 className="text-4xl font-black uppercase tracking-widest mb-2">Waiting Room</h1>
          <p className="text-slate-400 mb-8">Room Code: <span className="text-emerald-400 font-bold">{roomCode}</span></p>
          
          <div className="bg-slate-950 rounded-xl p-6 mb-8 border border-slate-800 min-h-[200px]">
            <h2 className="text-sm font-bold text-slate-500 uppercase tracking-widest mb-4">Joined Players ({competitors.length})</h2>
            <div className="flex flex-wrap justify-center gap-3">
              {competitors.map((comp: any) => (
                <div key={comp.username} className="bg-slate-800 px-4 py-2 rounded-lg font-bold border border-slate-700">
                  {comp.username} {comp.username === session?.username && "(You)"}
                </div>
              ))}
            </div>
          </div>

          {/* HOST CONTROLS */}
          {session?.participantId === lobbyHostId ? (
            <>
              <button 
                onClick={startAuction}
                className="w-full bg-emerald-600 hover:bg-emerald-500 text-white font-black py-4 px-4 rounded-xl text-xl transition-all uppercase tracking-widest shadow-lg active:scale-95"
              >
                Start Auction
              </button>
              <p className="text-xs text-slate-500 mt-4">Make sure everyone is in the room before starting.</p>
            </>
          ) : (
            <div className="bg-slate-800/50 border border-slate-700 rounded-xl py-6 animate-pulse">
              <p className="text-slate-400 font-bold uppercase tracking-widest flex items-center justify-center gap-2">
                <Activity className="w-5 h-5 text-emerald-500" />
                Waiting for host to start...
              </p>
            </div>
          )}
          <p className="text-xs text-slate-500 mt-4">Make sure everyone is in the room before starting.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col">
      
      {/* HEADER TIER */}
      <header className="border-b border-slate-800 bg-slate-900/50 p-4 flex justify-between items-center px-6">
        <div>
          <h1 className="text-xl font-black text-white flex items-center gap-2 uppercase tracking-widest">
            <Gavel className="text-blue-500 w-5 h-5" /> Live Auction
          </h1>
          <div className="text-xs font-bold text-slate-400 mt-1 flex items-center gap-2">
            Room: <span className="text-blue-400 bg-blue-900/30 px-2 py-0.5 rounded border border-blue-800">{roomCode}</span>
          </div>
        </div>

        <button 
          onClick={requestFinishAuction}
          className="bg-slate-900 border border-indigo-500/50 text-indigo-400 hover:bg-indigo-950 hover:text-indigo-300 font-black uppercase tracking-widest text-xs rounded-xl shadow-md transition-all flex flex-col items-center justify-center"
        >
          <Activity className="w-4 h-4 mb-1" />
            Analyze Teams
        </button>

        <div className="flex items-center gap-4">
          <div className="text-right">
            <p className="text-[10px] uppercase font-bold text-slate-500 tracking-wider">Playing As</p>
            <p className="text-sm font-black text-white">{session.username}</p>
          </div>
          <div className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full border text-xs font-bold ${isConnected ? "bg-emerald-950/40 border-emerald-900 text-emerald-400" : "bg-red-950/40 border-red-900 text-red-400"}`}>
            {isConnected ? <Activity className="w-3.5 h-3.5" /> : <AlertTriangle className="w-3.5 h-3.5" />}
            {isConnected ? "Connected" : "Disconnected"}
          </div>
        </div>

        
      </header>

      {/* MAIN BATTLEGROUND */}
      <main className="flex-grow p-6 grid grid-cols-1 lg:grid-cols-12 gap-6 max-w-7xl mx-auto w-full">
        
        {/* LEFT COLUMN: The Block & Action (8 cols) */}
        <div className="lg:col-span-8 flex flex-col gap-6">
          
          {/* THE AUCTION BLOCK */}
          <div className="bg-gradient-to-br from-slate-900 to-slate-950 border border-slate-800 rounded-2xl p-8 flex flex-col items-center justify-center text-center shadow-2xl relative overflow-hidden">
            <div className="absolute top-0 w-full h-1 bg-gradient-to-r from-blue-600 to-indigo-600"></div>
            
            <span className="bg-slate-800 text-slate-300 text-[10px] uppercase font-black tracking-widest px-3 py-1 rounded-full mb-6">On The Block</span>
            
            <h2 className="text-4xl font-black text-white mb-2">
              {playerOnBlock ? playerOnBlock.name : "Loading..."}
            </h2>
            <div className="flex items-center gap-3 text-sm text-slate-400 font-medium mb-8">
              <span className="bg-slate-900 px-3 py-1 rounded border border-slate-800">
                {playerOnBlock ? playerOnBlock.role : "..."}
              </span>
              <span className="bg-slate-900 px-3 py-1 rounded border border-slate-800">
                Base: ₹{playerOnBlock ? playerOnBlock.base_price : "0"}L
              </span>
            </div>

            {/* LIVE BID STATUS */}
            <div className="w-full bg-slate-950 border border-slate-800 rounded-xl p-6 flex items-center justify-between relative overflow-hidden">
              
              {/* The flashing timer background effect */}
              {timeLeft !== null && timeLeft <= 5 && timeLeft > 0 && (
                <div className="absolute inset-0 bg-red-900/20 animate-pulse"></div>
              )}

              <div className="text-left relative z-10">
                <p className="text-xs uppercase font-bold text-slate-500 tracking-wider mb-1">Current Highest Bid</p>
                <p className="text-3xl font-black text-emerald-400 flex items-center gap-2">
                  ₹{currentBid} <span className="text-lg">Lakhs</span>
                </p>
              </div>

              {/* NEW: The Countdown Clock */}
              {timeLeft !== null && timeLeft > 0 && (
                <div className="text-center relative z-10 px-4">
                  <p className="text-3xl font-black text-red-500">{timeLeft}s</p>
                  <p className="text-[9px] uppercase font-bold text-red-500/70 tracking-widest">Going...</p>
                </div>
              )}

              <div className="text-right relative z-10">
                <p className="text-xs uppercase font-bold text-slate-500 tracking-wider mb-1">Highest Bidder</p>
                <p className="text-xl font-bold text-white">{highestBidder}</p>
              </div>
            </div>
          </div>

          {/* PLAYER CONTROLS */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="bg-slate-900/50 border border-slate-800 rounded-xl p-3 flex flex-col justify-between shadow-inner">
              <div className="flex justify-between items-center border-b border-slate-800 pb-2 mb-2">
                <span className="text-[10px] uppercase font-bold text-slate-500 tracking-wider">Purse</span>
                <span className="text-lg font-black text-emerald-400">₹{myPurse}L</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-[10px] uppercase font-bold text-slate-500 tracking-wider">Slots Filled</span>
                <span className="text-lg font-black text-white">
                  {squadSize} <span className="text-slate-600 text-sm">/ 15</span>
                </span>
              </div>
            </div>

            <button 
              onClick={voteForceSell}
              disabled={!isConnected || hasVoted}
              className={`border rounded-xl font-black uppercase tracking-widest text-xs flex flex-col items-center justify-center transition-all shadow-md
                ${hasVoted 
                  ? "bg-slate-800 border-slate-700 text-slate-400 opacity-70" 
                  : "bg-slate-900 border-slate-700 text-slate-300 hover:bg-slate-800 hover:text-white"}`}
            >
              <div className="flex items-center gap-1.5 mb-1">
                <FastForward className="w-4 h-4" />
                <span>{hasVoted ? "Waiting on others" : "Pass / End"}</span>
              </div>
              {voteCount.required > 0 && (
                <span className="text-[9px] text-blue-400 font-bold bg-blue-950/50 px-2 py-0.5 rounded">
                  {voteCount.current} / {voteCount.required} Voted
                </span>
              )}
            </button>

            <button 
              onClick={placeBid}
              disabled={!isConnected || timeLeft === 0 || highestBidder === session.username || squadSize >= 15 || (currentBid + 50) > myPurse} 
              className="bg-gradient-to-r from-emerald-600 to-emerald-500 hover:from-emerald-500 hover:to-emerald-400 disabled:opacity-50 text-white font-black uppercase tracking-widest text-lg rounded-xl shadow-lg transition-all active:scale-95 flex items-center justify-center gap-2 py-4"
            >
              <Gavel className="w-5 h-5" />
              {squadSize >= 15 ? "Squad Full (Max 15)" :
               (currentBid + 50) > myPurse ? "Insufficient Funds" :
               highestBidder === session.username ? "You hold the bid" : 
               `Bid ₹${currentBid + 50}L`}
            </button>
          </div>

          {/* COMPETITOR ROSTERS (CACHED) */}
          <div className="mt-8 bg-slate-900/50 rounded-xl p-4 border border-slate-800">
            <h3 className="text-xs font-bold text-slate-500 uppercase tracking-widest mb-4">Lobby Participants</h3>
            <div className="flex flex-wrap gap-4">
              {competitors.map((comp: any) => (
                <details key={comp.username} className="group bg-slate-800 rounded-lg p-3 min-w-[200px] cursor-pointer">
                  <summary className="flex justify-between items-center font-bold text-white outline-none">
                    <span>{comp.username}</span>
                    <span className="text-emerald-400 text-sm">₹{comp.purse}L</span>
                  </summary>
                  <div className="mt-3 pt-3 border-t border-slate-700 text-sm text-slate-300 space-y-1 max-h-32 overflow-y-auto">
                    {comp.roster.length === 0 ? (
                      <span className="text-slate-500 italic">No players yet</span>
                    ) : (
                      comp.roster.map((p: any, idx: number) => (
                        <div key={idx} className="flex justify-between">
                          <span className="truncate pr-2">{p.name}</span>
                          <span className="text-emerald-500">₹{p.price}L</span>
                        </div>
                      ))
                    )}
                  </div>
                </details>
              ))}
            </div>
          </div>

        </div>

        {/* RIGHT COLUMN: Activity Feed (4 cols) */}
        <div className="lg:col-span-4 bg-slate-900/40 border border-slate-800 rounded-2xl flex flex-col overflow-hidden">
          <div className="p-4 border-b border-slate-800 bg-slate-900/60 flex items-center gap-2">
            <History className="w-4 h-4 text-blue-400" />
            <h3 className="text-xs font-black uppercase tracking-wider text-slate-300">Live Event Feed</h3>
          </div>
          
          <div className="flex-grow p-4 overflow-y-auto space-y-3 max-h-[500px]">
            {logs.length === 0 ? (
              <p className="text-xs text-slate-500 font-medium text-center py-10">Awaiting auction commencement...</p>
            ) : (
              logs.map((log) => (
                <div 
                  key={log.id} 
                  className={`text-xs p-3 rounded-lg border leading-relaxed ${
                    log.type === "system" 
                      ? "bg-slate-950 border-slate-800 text-slate-400" 
                      : "bg-blue-950/20 border-blue-900/50 text-blue-200"
                  }`}
                >
                  {log.text}
                </div>
              ))
            )}
          </div>
        </div>

      </main>
    </div>
  );
}