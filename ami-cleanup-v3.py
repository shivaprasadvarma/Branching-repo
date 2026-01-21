import boto3
import csv
import logging

# Configure logging
logging.basicConfig(filename='ami_cleanup.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def delete_ami_and_snapshots(ami_id, region):
    ec2_client = boto3.client('ec2', region_name=region)

    # Strip whitespace and remove non-printable characters
    ami_id_clean = ''.join(c for c in ami_id if c.isalnum() or c in '-_')

    # Log the sanitized AMI ID
    logging.info(f"Sanitized AMI ID: '{ami_id_clean}'")

    try:
        response = ec2_client.describe_images(ImageIds=[ami_id_clean])
    except boto3.exceptions.botocore.exceptions.ClientError as e:
        logging.error(f"Error describing AMI {ami_id_clean}: {e}")
        return

    if not response['Images']:
        logging.warning(f"AMI with ID {ami_id_clean} not found.")
        return

    snapshot_ids = []
    for block_device in response['Images'][0]['BlockDeviceMappings']:
        ebs_info = block_device.get('Ebs', None)
        if ebs_info:
            snapshot_id = ebs_info.get('SnapshotId', None)
            if snapshot_id:
                snapshot_ids.append(snapshot_id)

    try:
        ec2_client.deregister_image(ImageId=ami_id_clean)
        logging.info(f"AMI {ami_id_clean} deregistered successfully.")
    except boto3.exceptions.botocore.exceptions.ClientError as e:
        logging.error(f"Error deregistering AMI {ami_id_clean}: {e}")
        return

    for snapshot_id in snapshot_ids:
        try:
            ec2_client.delete_snapshot(SnapshotId=snapshot_id)
            logging.info(f"Snapshot {snapshot_id} deleted successfully.")
        except boto3.exceptions.botocore.exceptions.ClientError as e:
            logging.error(f"Error deleting snapshot {snapshot_id}: {e}")

    logging.info(f"AMI {ami_id_clean} and its associated snapshots deleted successfully.")

if __name__ == "__main__":
    csv_file_path = 'cleanup.csv'
    region = 'ap-south-1'  # Replace 'your_region' with the actual AWS region

    print("Starting AMI cleanup...")

    try:
        with open(csv_file_path, 'r') as csvfile:
            reader = csv.reader(csvfile)
            next(reader)  # Skip the header row
            for row in reader:
                ami_id_to_delete = row[0].strip()
                print(f"Deleting AMI {ami_id_to_delete} and its snapshots...")
                delete_ami_and_snapshots(ami_id_to_delete, region)
                print(f"AMI {ami_id_to_delete} cleanup completed.")
    except FileNotFoundError as e:
        logging.error(f"CSV file {csv_file_path} not found: {e}")
    except Exception as e:
        logging.error(f"An error occurred while processing the CSV file: {e}")

    print("AMI cleanup process finished.")
