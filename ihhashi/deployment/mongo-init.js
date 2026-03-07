// MongoDB initialization script
// Creates application user with appropriate permissions

db = db.getSiblingDB('ihhashi');

// Create application user
db.createUser({
  user: 'ihhashi_app',
  pwd: _getEnv('MONGO_PASSWORD'),
  roles: [
    {
      role: 'readWrite',
      db: 'ihhashi'
    }
  ]
});

// Create initial collections with validation
db.createCollection('users', {
  validator: {
    $jsonSchema: {
      bsonType: 'object',
      required: ['email', 'role', 'created_at']
    }
  }
});

db.createCollection('merchants');
db.createCollection('orders');
db.createCollection('products');
db.createCollection('trips');
db.createCollection('delivery_servicemen');
db.createCollection('refunds');
db.createCollection('_migrations');

print('✅ iHhashi database initialized');
