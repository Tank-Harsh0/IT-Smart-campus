from django.core.management.base import BaseCommand
from apps.subjects.models import Subject


class Command(BaseCommand):
    help = 'Populate GTU IT Department subjects with syllabus URLs'

    def handle(self, *args, **options):
        # Clear existing subjects
        Subject.objects.all().delete()
        self.stdout.write("Cleared existing subjects...")

        subjects_data = [
            # ===== SEMESTER 1 =====
            {"code": "DI01000011", "name": "Induction Programme with Essence of Indian Knowledge", "semester": 1, "syllabus_url": "https://s3-ap-southeast-1.amazonaws.com/gtusitecirculars/Syallbus/DI01000011.pdf"},
            {"code": "DI01000021", "name": "Mathematics-I", "semester": 1, "syllabus_url": "https://s3-ap-southeast-1.amazonaws.com/gtusitecirculars/Syallbus/DI01000021.pdf"},
            {"code": "DI01000031", "name": "Communication Skills in English", "semester": 1, "syllabus_url": "https://s3-ap-southeast-1.amazonaws.com/gtusitecirculars/Syallbus/DI01000031.pdf"},
            {"code": "DI01000041", "name": "Sports and Yoga", "semester": 1, "syllabus_url": "https://s3-ap-southeast-1.amazonaws.com/gtusitecirculars/Syallbus/DI01000041.pdf"},
            {"code": "DI01000071", "name": "Engineering Chemistry", "semester": 1, "syllabus_url": "https://s3-ap-southeast-1.amazonaws.com/gtusitecirculars/Syallbus/DI01000071.pdf"},
            {"code": "DI01016011", "name": "Python Programming", "semester": 1, "syllabus_url": "https://s3-ap-southeast-1.amazonaws.com/gtusitecirculars/Syallbus/DI01016011.pdf"},
            {"code": "DI01016021", "name": "Introduction to I.T. Systems", "semester": 1, "syllabus_url": "https://s3-ap-southeast-1.amazonaws.com/gtusitecirculars/Syallbus/DI01016021.pdf"},
            {"code": "DI01016031", "name": "Web Development using PHP", "semester": 1, "syllabus_url": "https://s3-ap-southeast-1.amazonaws.com/gtusitecirculars/Syallbus/DI01016031.pdf"},
            
            # ===== SEMESTER 2 =====
            {"code": "DI01000061", "name": "Modern Physics", "semester": 2, "syllabus_url": "https://s3-ap-southeast-1.amazonaws.com/gtusitecirculars/Syallbus/DI01000061.pdf"},
            {"code": "DI02000011", "name": "Applied Mathematics", "semester": 2, "syllabus_url": "https://s3-ap-southeast-1.amazonaws.com/gtusitecirculars/Syallbus/DI02000011.pdf"},
            {"code": "DI02000051", "name": "Environmental Sustainability", "semester": 2, "syllabus_url": "https://s3-ap-southeast-1.amazonaws.com/gtusitecirculars/Syallbus/DI02000051.pdf"},
            {"code": "DI02000061", "name": "Indian Constitution", "semester": 2, "syllabus_url": "https://s3-ap-southeast-1.amazonaws.com/gtusitecirculars/Syallbus/DI02000061.pdf"},
            {"code": "DI02000131", "name": "Contributor Personality Development", "semester": 2, "syllabus_url": "https://s3-ap-southeast-1.amazonaws.com/gtusitecirculars/Syallbus/DI02000131.pdf"},
            {"code": "DI02016011", "name": "Advanced Python Programming", "semester": 2, "syllabus_url": "https://s3-ap-southeast-1.amazonaws.com/gtusitecirculars/Syallbus/DI02016011.pdf"},
            {"code": "DI02016021", "name": "Fundamentals of Software Development", "semester": 2, "syllabus_url": "https://s3-ap-southeast-1.amazonaws.com/gtusitecirculars/Syallbus/DI02016021.pdf"},
            
            # ===== SEMESTER 3 =====
            {"code": "DI03016011", "name": "Digital Marketing", "semester": 3, "syllabus_url": "https://s3-ap-southeast-1.amazonaws.com/gtusitecirculars/Syallbus/DI03016011.pdf"},
            {"code": "DI03016021", "name": "Cryptography and Web Security", "semester": 3, "syllabus_url": "https://s3-ap-southeast-1.amazonaws.com/gtusitecirculars/Syallbus/DI03016021.pdf"},
            {"code": "DI03016031", "name": "Data Structures with Python", "semester": 3, "syllabus_url": "https://s3-ap-southeast-1.amazonaws.com/gtusitecirculars/Syallbus/DI03016031.pdf"},
            {"code": "DI03016041", "name": "Database Management", "semester": 3, "syllabus_url": "https://s3-ap-southeast-1.amazonaws.com/gtusitecirculars/Syallbus/DI03016041.pdf"},
            {"code": "DI03016051", "name": "Object Oriented Programming with JAVA", "semester": 3, "syllabus_url": "https://s3-ap-southeast-1.amazonaws.com/gtusitecirculars/Syallbus/DI03016051.pdf"},
            {"code": "DI03016061", "name": "Operating Systems", "semester": 3, "syllabus_url": "https://s3-ap-southeast-1.amazonaws.com/gtusitecirculars/Syallbus/DI03016061.pdf"},
            
            # ===== SEMESTER 4 =====
            {"code": "DI04000081", "name": "Entrepreneurship & Start-up", "semester": 4, "syllabus_url": "https://s3-ap-southeast-1.amazonaws.com/gtusitecirculars/Syallbus/DI04000081.pdf"},
            {"code": "DI04016011", "name": "Mobile Computing and Networks", "semester": 4, "syllabus_url": "https://s3-ap-southeast-1.amazonaws.com/gtusitecirculars/Syallbus/DI04016011.pdf"},
            {"code": "DI04016021", "name": "Cyber Security and Digital Forensics", "semester": 4, "syllabus_url": "https://s3-ap-southeast-1.amazonaws.com/gtusitecirculars/Syallbus/DI04016021.pdf"},
            {"code": "DI04016031", "name": "Fundamental of Machine Learning", "semester": 4, "syllabus_url": "https://s3-ap-southeast-1.amazonaws.com/gtusitecirculars/Syallbus/DI04016031.pdf"},
            {"code": "DI04016041", "name": "UI and UX Design", "semester": 4, "syllabus_url": "https://s3-ap-southeast-1.amazonaws.com/gtusitecirculars/Syallbus/DI04016041.pdf"},
            {"code": "DI04016051", "name": "Mobile Application Development", "semester": 4, "syllabus_url": "https://s3-ap-southeast-1.amazonaws.com/gtusitecirculars/Syallbus/DI04016051.pdf"},
            {"code": "DI04016061", "name": "Database Administration", "semester": 4, "syllabus_url": "https://s3-ap-southeast-1.amazonaws.com/gtusitecirculars/Syallbus/DI04016061.pdf"},
            {"code": "DI04016071", "name": "Advanced Java Programming", "semester": 4, "syllabus_url": "https://s3-ap-southeast-1.amazonaws.com/gtusitecirculars/Syallbus/DI04016071.pdf"},
            {"code": "DI04016081", "name": "Data Mining and Warehousing", "semester": 4, "syllabus_url": "https://s3-ap-southeast-1.amazonaws.com/gtusitecirculars/Syallbus/DI04016081.pdf"},
            
            # ===== SEMESTER 5 =====
            {"code": "4300021", "name": "Entrepreneurship and Start-ups", "semester": 5, "syllabus_url": "https://s3-ap-southeast-1.amazonaws.com/gtusitecirculars/Syallbus/4300021.pdf"},
            {"code": "4351601", "name": "Foundation of AI and ML", "semester": 5, "syllabus_url": "https://s3-ap-southeast-1.amazonaws.com/gtusitecirculars/Syallbus/4351601.pdf"},
            {"code": "4351602", "name": "Mobile Computing and Networks", "semester": 5, "syllabus_url": "https://s3-ap-southeast-1.amazonaws.com/gtusitecirculars/Syallbus/4351602.pdf"},
            {"code": "4351603", "name": "Advanced Java Programming", "semester": 5, "syllabus_url": "https://s3-ap-southeast-1.amazonaws.com/gtusitecirculars/Syallbus/4351603.pdf"},
            {"code": "4351604", "name": "Mobile Application Development", "semester": 5, "syllabus_url": "https://s3-ap-southeast-1.amazonaws.com/gtusitecirculars/Syallbus/4351604.pdf"},
            {"code": "4351605", "name": "Summer Internship-II", "semester": 5, "syllabus_url": "https://s3-ap-southeast-1.amazonaws.com/gtusitecirculars/Syallbus/4351605.pdf"},
            
            # ===== SEMESTER 6 =====
            {"code": "4361601", "name": "ASP.NET and VB.NET Web Programming", "semester": 6, "syllabus_url": "https://s3-ap-southeast-1.amazonaws.com/gtusitecirculars/Syallbus/2361601%20.pdf"},
            {"code": "4361602", "name": "Information Security", "semester": 6, "syllabus_url": "https://s3-ap-southeast-1.amazonaws.com/gtusitecirculars/Syallbus/2361602%20.pdf"},
            {"code": "4361603", "name": "Cloud Computing", "semester": 6, "syllabus_url": ""},
            {"code": "4361604", "name": "Enterprise Resource Planning", "semester": 6, "syllabus_url": "https://s3-ap-southeast-1.amazonaws.com/gtusitecirculars/Syallbus/2361604.pdf"},
            {"code": "4361605", "name": "Project Work", "semester": 6, "syllabus_url": ""},
        ]

        for subj in subjects_data:
            Subject.objects.create(
                code=subj["code"],
                name=subj["name"],
                semester=subj["semester"],
                syllabus_url=subj["syllabus_url"] if subj["syllabus_url"] else None,
            )

        self.stdout.write(self.style.SUCCESS(f'Successfully created {Subject.objects.count()} subjects!'))
        
        # Summary by semester
        for sem in range(1, 7):
            count = Subject.objects.filter(semester=sem).count()
            self.stdout.write(f'  Semester {sem}: {count} subjects')
