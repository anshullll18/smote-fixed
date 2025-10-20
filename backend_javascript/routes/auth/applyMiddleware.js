const jwt = require('jsonwebtoken');
const User = require('../../models/User'); 

async function applyMiddleware(req, res, next) {
  try {
    const raw = req.headers.authorization || '';
    const token = raw.startsWith('Bearer ') ? raw.slice(7) : null;
    if (!token) return res.status(401).json({ message: 'No token provided' });
    console.log(token); //remove this later
    const payload = jwt.verify(token, process.env.JWT_SECRET);
    const user = await User.findById(payload.id).select('-password');
    if (!user) return res.status(401).json({ message: 'Invalid token' });
    req.userId = user._id;
    req.userSafe = user;
    next();
  } catch {
    return res.status(401).json({ message: 'Invalid token' });
  }
}

module.exports = { applyMiddleware };
