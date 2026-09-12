const { Client } = require('pg');
const client = new Client({
  host: 'localhost',
  port: 5432,
  user: 'user',
  password: 'enter pass',
  database: 'ai mart',
});
client.connect()
  .then(() => {
    console.log('Connected successfully');
    return client.query('SELECT 1');
  })
  .then(res => {
    console.log('Query result:', res.rows[0]);
    process.exit(0);
  })
  .catch(e => {
    console.error('Connection error:', e);
    process.exit(1);
  })
  .finally(() => client.end());
