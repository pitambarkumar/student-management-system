students = []

while True:
    print("=== Student Management System ===")
    print("1. Add student")
    print("2. View students")
    print("3. Search student")
    print("4. Update student")
    print("5. Delete student")
    print("6. Exit")

    choice = input("Enter your choice: ")

    if choice == "1":
        print("Adding a new student...")

        name = input("Enter student name: ")
        age = input("Enter student age: ")
        course = input("Enter student course: ")

        student = {
            "name": name,
            "age": age,
            "course": course
        }

        students.append(student)

        print(f"Student {name} added successfully.")

    elif choice == "2":
        print("Option 2 working")

    elif choice == "3":
        search_name = input("Enter student name to search: ")

        for student in students:
            if student["name"].lower() == search_name.lower():
                print(
                    f"Name: {student['name']}, "
                    f"Age: {student['age']}, "
                    f"Course: {student['course']}"
                )
                break
        else:
            print("Student not found.")

    elif choice == "4":
        print("Update student")

    elif choice == "5":
        print("Delete student")

    elif choice == "6":
        print("Exiting program...")
        break

    else:
        print("Invalid choice!")