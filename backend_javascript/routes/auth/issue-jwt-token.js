const jwt = require('jsonwebtoken');

module.exports = function issueJwtToken(req, res) {
  const u = req.authUser;
  const token = jwt.sign({ id: u._id }, process.env.JWT_SECRET, { expiresIn: '7d' });
  const status = req.method === 'POST' && req.path.endsWith('register') ? 201 : 200;
  return res.status(status).json({
    token,
    user: { id: u._id, username: u.username, email: u.email },
  });
};
