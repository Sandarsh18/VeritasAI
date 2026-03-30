import { motion } from "framer-motion";

const containerVariants = {
  hidden: { opacity: 0, scale: 0.95, y: 30 },
  visible: { 
    opacity: 1, 
    scale: 1, 
    y: 0,
    transition: { type: "spring", stiffness: 300, damping: 25, staggerChildren: 0.1 } 
  },
  exit: { opacity: 0, scale: 0.95, y: -20, transition: { duration: 0.2 } }
};

const itemVariants = {
  hidden: { opacity: 0, x: -20 },
  visible: { opacity: 1, x: 0, transition: { type: "spring", stiffness: 300 } }
};

function Profile({ user, onLogout }) {
  if (!user) return null;

  return (
    <motion.div 
      className="page"
      initial="hidden"
      animate="visible"
      exit="exit"
      variants={containerVariants}
    >
      <motion.div 
        className="card profile-card"
        whileHover={{ boxShadow: "0 10px 40px rgba(0,0,0,0.15)" }}
      >
        <motion.h2 variants={itemVariants}>User Profile</motion.h2>

        <div className="profile-grid">
          <motion.div className="card" variants={itemVariants} whileHover={{ scale: 1.05 }}>
            <label>Username</label>
            <p>{user.username}</p>
          </motion.div>
          
          <motion.div className="card" variants={itemVariants} whileHover={{ scale: 1.05 }}>
            <label>Email Address</label>
            <p>{user.email}</p>
          </motion.div>

          <motion.div className="card" variants={itemVariants} whileHover={{ scale: 1.05 }}>
            <label>Account Status</label>
            <p style={{ color: user.is_active ? 'var(--true)' : 'var(--false)' }}>
              {user.is_active ? 'Active' : 'Inactive'}
            </p>
          </motion.div>

          <motion.div className="card" variants={itemVariants} whileHover={{ scale: 1.05 }}>
            <label>Verification Standard</label>
            <p>Verified ✔</p>
          </motion.div>
        </div>

        <motion.div variants={itemVariants} style={{ display: 'flex', justifyContent: 'flex-end', marginTop: '1.5rem' }}>
          <motion.button 
            className="primary-btn" 
            onClick={onLogout} 
            style={{ backgroundColor: 'var(--false)' }}
            whileHover={{ scale: 1.05, filter: 'brightness(1.1)' }}
            whileTap={{ scale: 0.95 }}
          >
            Logout
          </motion.button>
        </motion.div>
      </motion.div>
    </motion.div>
  );
}

export default Profile;
