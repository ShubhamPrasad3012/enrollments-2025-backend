import boto3
from botocore.exceptions import ClientError
import json
from datetime import datetime
from dotenv import load_dotenv
from os import getenv


class DynamoDBManager:
    def __init__(self):
        load_dotenv()
        self.dynamodb = boto3.resource(
            'dynamodb',
            region_name=getenv('AWS_REGION'),
            aws_access_key_id=getenv('AWS_ACCESS_KEY'),
            aws_secret_access_key=getenv('AWS_SECRET_KEY')
        )

        self.table_configs = {
            "enrollments-site-users": {
                "key_field": "uid",
                "required_fields": ["name"] # to be configured as per schema
            },
            "enrollments-site-quiz": {
                "key_field": "qid",
                "required_fields": []
            },
                    "enrollments-site-interview":{
                "key_field": "iid",
                "required_fields": []
                    },
                    "enrollments-site-task":{
                "key_field": "tid",
                "required_fields": []
                    }
                            }
        
        # Initialize table objects
        self.tables = {
            table_name: self.dynamodb.Table(table_name)
            for table_name in self.table_configs
        }

    def add_item(self, table_name: str) -> None:
        """Add a new item to specified table"""
        if table_name not in self.tables:
            print(f"\n❌ Table {table_name} not found!")
            return
            
        config = self.table_configs[table_name]
        print(f"\n=== Add New Item to {table_name} ===")
        
        # Get primary key
        key_value = input(f"Enter {config['key_field']}: ")
        
        # Build item dictionary
        item = {
            config['key_field']: key_value,
            "created_at": str(datetime.now())
        }
        
        # Get required fields
        for field in config['required_fields']:
            item[field] = input(f"Enter {field}: ")
        
        # Optional: allow additional fields
        while True:
            add_field = input("\nAdd additional field? (y/n): ").lower()
            if add_field != 'y':
                break
            field_name = input("Enter field name: ")
            field_value = input(f"Enter value for {field_name}: ")
            item[field_name] = field_value

        try:
            self.tables[table_name].put_item(Item=item)
            print(f"\n✅ Item added successfully to {table_name}!")
        except ClientError as e:
            print(f"\n❌ Error adding item: {e.response['Error']['Message']}")

    def view_item(self, table_name: str) -> None:
        """View an item from specified table"""
        if table_name not in self.tables:
            print(f"\n❌ Table {table_name} not found!")
            return
            
        config = self.table_configs[table_name]
        key_value = input(f"Enter {config['key_field']}: ")
        
        try:
            response = self.tables[table_name].get_item(
                Key={config['key_field']: key_value}
            )
            if "Item" in response:
                print("\n=== Item Details ===")
                print(json.dumps(response["Item"], indent=2))
            else:
                print(f"\n❌ Item with {config['key_field']} '{key_value}' not found")
        except ClientError as e:
            print(f"\n❌ Error retrieving item: {e.response['Error']['Message']}")

    def delete_item(self, table_name: str) -> None:
        """Delete an item from specified table"""
        if table_name not in self.tables:
            print(f"\n❌ Table {table_name} not found!")
            return
            
        config = self.table_configs[table_name]
        key_value = input(f"Enter {config['key_field']} to delete: ")
        
        try:
            self.tables[table_name].delete_item(
                Key={config['key_field']: key_value}
            )
            print(f"\n✅ Item deleted successfully from {table_name}!")
        except ClientError as e:
            print(f"\n❌ Error deleting item: {e.response['Error']['Message']}")

    def list_all_items(self, table_name: str) -> None:
        """List all items in specified table"""
        if table_name not in self.tables:
            print(f"\n❌ Table {table_name} not found!")
            return
            
        try:
            response = self.tables[table_name].scan()
            items = response.get("Items", [])
            
            if not items:
                print(f"\n📝 No items found in {table_name}")
                return
                
            print(f"\n=== All Items in {table_name} ===")
            for item in items:
                print(json.dumps(item, indent=2))
                print("-" * 40)
            
            print(f"\nTotal items: {len(items)}")
        except ClientError as e:
            print(f"\n❌ Error listing items: {e.response['Error']['Message']}")

    def get_table_choice(self) -> str:
        """Get user's table choice"""
        print("\nAvailable tables:")
        for i, table_name in enumerate(self.tables.keys(), 1):
            print(f"{i}. {table_name}")
        
        while True:
            try:
                choice = int(input("\nSelect table (enter number): "))
                if 1 <= choice <= len(self.tables):
                    return list(self.tables.keys())[choice - 1]
                print("❌ Invalid choice!")
            except ValueError:
                print("❌ Please enter a number!")

    def display_menu(self) -> None:
        """Display the main menu"""
        print("\n=== DynamoDB Management System ===")
        print("1. Add new item")
        print("2. View item")
        print("3. Delete item")
        print("4. List all items")
        print("5. Exit")

    def run(self) -> None:
        """Main program loop"""
        while True:
            self.display_menu()
            choice = input("\nEnter your choice (1-5): ")
            
            if choice == "5":
                print("\n👋 Goodbye!")
                break
                
            if choice not in ["1", "2", "3", "4"]:
                print("\n❌ Invalid choice. Please try again.")
                continue
                
            table_name = self.get_table_choice()
                
            if choice == "1":
                self.add_item(table_name)
            elif choice == "2":
                self.view_item(table_name)
            elif choice == "3":
                self.delete_item(table_name)
            elif choice == "4":
                self.list_all_items(table_name)

if __name__ == "__main__":
    manager = DynamoDBManager()
    manager.run()