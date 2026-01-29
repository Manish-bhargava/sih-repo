// --- Mock API Server for SIH Project Simulation ---
const express = require("express");
const cors = require("cors");
const bodyParser = require("body-parser");
const fs = require("fs");
const csv = require("csv-parser");
const path = require("path");

const app = express();
const PORT = process.env.PORT || 5001;

// --- Middleware ---
app.use(cors());
app.use(bodyParser.json());

// --- Load CSV Simulation Data ---
let df_simulation = [];
const csvPath = path.join(__dirname, "simulation_paths.csv");

if (fs.existsSync(csvPath)) {
  fs.createReadStream(csvPath)
    .pipe(csv())
    .on("data", (row) => df_simulation.push(row))
    .on("end", () => console.log("✅ 'simulation_paths.csv' loaded."))
    .on("error", (err) => console.error("❌ CSV Error:", err));
}

// --- User Authentication Data ---
const authUsersFile = path.join(__dirname, 'authUsers.json');
let authUsers = [];

if (!fs.existsSync(authUsersFile)) {
    fs.writeFileSync(authUsersFile, JSON.stringify([], null, 2));
} else {
    try {
        const data = fs.readFileSync(authUsersFile, 'utf8');
        authUsers = data ? JSON.parse(data) : [];
    } catch (e) { 
        authUsers = []; 
    }
}

function saveAuthUsers() {
  try { 
    fs.writeFileSync(authUsersFile, JSON.stringify(authUsers, null, 2)); 
  } catch (e) { 
    console.error('Error saving auth users:', e); 
  }
}

// --- API Routes (MUST come before static serving) ---

app.get("/get_live_statuses", (req, res) => {
  res.json(df_simulation);
});

app.get("/get_tourist_ids", (req, res) => {
  const normal = [...new Set(df_simulation.filter(r => r.path_type === "normal").map(r => r.tourist_id))];
  const anomaly = [...new Set(df_simulation.filter(r => r.path_type === "anomaly").map(r => r.tourist_id))];
  res.json({ normal, anomaly });
});

app.post("/register", (req, res) => {
  const { username, email, phone } = req.body;
  if (!username || !phone) return res.status(400).json({ error: "Username and Phone are required" });
  const newUser = { id: Date.now().toString(), username, email: email || "", phone };
  authUsers.push(newUser);
  saveAuthUsers();
  res.json({ success: true, message: "Registered successfully" });
});

app.post("/login", (req, res) => {
  const { username, phone } = req.body;
  const user = authUsers.find(u => (username && u.username === username) || (phone && u.phone === phone));
  if (!user) return res.status(404).json({ error: "User not found" });
  res.json({ success: true, user: { id: user.id, username: user.username } });
});

// --- Static Frontend Serving ---
const frontendPath = path.join(__dirname, "../live-dashboard/out");
app.use(express.static(frontendPath));

/**
 * FINAL FIX FOR PathError:
 * The syntax "(.*)" or "*" without a name is no longer supported.
 * ":any(.*)" gives the parameter a name while capturing all sub-paths.
 */
app.get("/:any(.*)", (req, res) => {
  const indexPath = path.join(frontendPath, "index.html");
  if (fs.existsSync(indexPath)) {
    res.sendFile(indexPath);
  } else {
    res.status(404).send("Frontend build not found. Ensure your 'out' directory exists.");
  }
});

app.listen(PORT, '0.0.0.0', () => {
  console.log(`🚀 Server running on port ${PORT}`);
});