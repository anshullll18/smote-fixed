function validateRegister(req, res, next) {
  const { username, email, password } = req.creds || {};
  if (!username || !email || !password) {
    return res.status(400).json({ message: 'Missing fields' });
  }
  next();
}
function validateLogin(req, res, next) {
  const { email, password } = req.creds || {};
  if (!email || !password) {
    return res.status(400).json({ message: 'Missing fields' });
  }
  next();
}
module.exports = { validateRegister, validateLogin };
