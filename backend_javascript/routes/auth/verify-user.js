const bcrypt = require('bcryptjs');
const User = require('../../models/User');

module.exports = async function verifyUser(req, res, next) {
  try {
    const { email, password } = req.creds;
    const user = await User.findOne({ email });
    if (!user) return res.status(400).json({ message: 'Invalid credentials' });
    const ok = await bcrypt.compare(password, user.password);
    if (!ok) return res.status(400).json({ message: 'Invalid credentials' });
    req.authUser = user; 
    next();
  } catch (e) {
    console.error('Login error:', e);
    res.status(500).json({ message: 'Server error' });
  }
};
