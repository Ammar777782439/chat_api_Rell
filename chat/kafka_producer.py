from kafka import KafkaProducer
import json
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('kafka_producer')

class KafkaProducerService:
    """
    Service for sending messages to Kafka topics.

    This class provides a simple interface for sending messages to Kafka topics,
    with error handling and logging.
    """

    def __init__(self, bootstrap_servers):
        """
        Initialize the Kafka producer with the specified bootstrap servers.

        Args:
            bootstrap_servers (list): List of Kafka bootstrap servers in the format ['host:port']
        """
        self.bootstrap_servers = bootstrap_servers
        try:
            self.producer = KafkaProducer(
                bootstrap_servers=self.bootstrap_servers,
                value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                retries=5,  # Retry sending messages up to 5 times
                acks='all',  # Wait for all replicas to acknowledge the message
                request_timeout_ms=30000,  # 30 seconds timeout for requests
                max_block_ms=60000  # 60 seconds max blocking time
            )
            logger.info(f"Kafka producer initialized with bootstrap servers: {bootstrap_servers}")
        except Exception as e:
            logger.error(f"Failed to initialize Kafka producer: {e}")
            # Create a dummy producer that logs errors but doesn't crash the application
            self.producer = None

    def send_message(self, topic, message):
        """
        Send a message to the specified Kafka topic.

        Args:
            topic (str): The Kafka topic to send the message to
            message (dict): The message to send (will be serialized to JSON)

        Returns:
            bool: True if the message was sent successfully, False otherwise
        """
        if self.producer is None:
            logger.error(f"Cannot send message to topic '{topic}': Kafka producer not initialized")
            return False

        try:
            # Send the message to Kafka
            future = self.producer.send(topic, message)
            # Wait for the message to be sent (this will raise an exception if it fails)
            future.get(timeout=10)
            # Flush to ensure the message is sent immediately
            self.producer.flush()
            logger.info(f"Message sent to topic '{topic}': {message}")
            return True
        except Exception as e:
            logger.error(f"Error sending message to topic '{topic}': {e}")
            return False

# Example usage (you'll need to adapt this to your application)
if __name__ == '__main__':
    producer_service = KafkaProducerService(bootstrap_servers=['192.168.117.128:9094'])
    message = {'user': 'test_user', 'message': 'Hello from Kafka!'}
    producer_service.send_message('chat_messages', message)
