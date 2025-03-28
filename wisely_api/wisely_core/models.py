from django.db import models
from django.contrib.auth.models import AbstractUser
from django.conf import settings


class User(AbstractUser):
    USER_TYPE_CHOICES = (
        ('professional', 'Professional'),
        ('client', 'Client'),
        ('business_admin', 'Business Admin')  # for future feature of moderator
    )
    user_type = models.CharField(choices=USER_TYPE_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.username


class Professional(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='professional_profile')
    bio = models.TextField()
    is_active = models.BooleanField(default=True)
    has_openings = models.BooleanField(default=False)
    last_active = models.DateTimeField(auto_now=True)
    profile_image = models.ImageField(upload_to='profile_images/', null=True, blank=True)
    contact_email = models.EmailField(null=True, blank=True)
    contact_phone = models.CharField(max_length=20, null=True, blank=True)
    saved_books = models.ManyToManyField('Book', blank=True, related_name='saved_by_professionals')

    def __str__(self):
        return f"{self.user.first_name} {self.user.last_name}"


class Client(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='client_profile')
    saved_books = models.ManyToManyField('Book', blank=True, related_name='saved_by_clients')

    def __str__(self):
        return f"{self.user.first_name} {self.user.last_name}"


# BOOKS


class Category(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    
    class Meta:
        verbose_name_plural = "Categories"
        
    def __str__(self):
        return self.name
    

class Book(models.Model):
    title = models.CharField(max_length=255)
    author = models.CharField(max_length=255)
    isbn = models.CharField(max_length=20, blank=True)
    year_published = models.IntegerField(null=True, blank=True)
    publisher = models.CharField(max_length=255, blank=True)
    cover_image = models.ImageField(upload_to='book_covers/', null=True, blank=True)
    description = models.TextField(blank=True)
    categories = models.ManyToManyField(Category, related_name='books')

    def __str__(self):
        return self.title


class Review(models.Model):
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name='reviews')
    professional = models.ForeignKey(Professional, on_delete=models.CASCADE, related_name='reviews')
    rating = models.IntegerField()
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('book', 'professional')

    def __str__(self):
        return f"Review by {self.professional} for {self.book}"


# LICENSURE


class License(models.Model):
    LICENSE_TYPE_CHOICES = (
        ('lcsw', 'Licensed Clinical Social Worker'),
        ('lmsw', 'Licensed Master Social Worker'),
        ('lmft', 'Licensed Marriage and Family Therapist'),
        ('lpc', 'Licensed Professional Counselor'),
        ('lmhc', 'Licensed Mental Health Counselor'),
        ('psychologist', 'Licensed Psychologist'),
        ('psychiatrist', 'Psychiatrist (MD)'),
        ('lpcc', 'Licensed Professional Clinical Counselor'),
        ('cadc', 'Certified Alcohol and Drug Counselor'),
    )

    license_type = models.CharField(max_length=50, choices=LICENSE_TYPE_CHOICES)

    @property
    def requirements(self):
        requirements = {
            'lcsw': 'A licensed clinical social worker is a professional who has obtained a master\'s degree in social work and has completed the required clinical training and supervision.',
            'lmsw': 'A licensed master social worker is a professional who has obtained a master\'s degree in social work and has passed the required licensing exam.',
            'lmft': 'A licensed marriage and family therapist is a professional who has obtained a master\'s or doctoral degree in marriage and family therapy and has completed the required clinical training and supervision.',
            'lpc': 'A licensed professional counselor is a professional who has obtained a master\'s degree in counseling and has completed the required clinical training and supervision.',
            'lmhc': 'A licensed mental health counselor is a professional who has obtained a master\'s degree in counseling and has completed the required clinical training and supervision.',
            'psychologist': 'A licensed psychologist is a professional who has obtained a doctoral degree in psychology and has completed the required clinical training and supervision.',
            'psychiatrist': 'A psychiatrist is a medical doctor (MD) who specializes in the diagnosis and treatment of mental health disorders.',
            'lpcc': 'A licensed professional clinical counselor is a professional who has obtained a master\'s degree in counseling and has completed the required clinical training and supervision.',
            'cadc': 'A certified alcohol and drug counselor is a professional who has obtained certification in the treatment of substance use disorders.',
        }

        return requirements.get(self.license_type, '')

    @property
    def description(self):
        descriptions = {
            'lcsw': 'A licensed mental health professional who is qualified to assess, diagnose, and treat mental health disorders.',
            'lmsw': 'A social worker with a master\'s degree who is licensed to practice social work but may have supervision requirements for clinical practice.',
            'lmft': 'A licensed mental health professional who specializes in marriage and family therapy.',
            'lpc': 'A licensed mental health professional who provides counseling and psychotherapy services.',
            'lmhc': 'A licensed mental health professional who provides counseling and psychotherapy services.',
            'psychologist': 'A licensed mental health professional with a doctoral degree in psychology who provides assessment and therapy services.',
            'psychiatrist': 'A medical doctor who specializes in the diagnosis and treatment of mental health disorders, including prescribing medication.',
            'lpcc': 'A licensed mental health professional who provides counseling and psychotherapy services.',
            'cadc': 'A certified professional who specializes in the treatment of substance use disorders.',
        }

        return descriptions.get(self.license_type, '')

    def __str__(self):
        return self.get_license_type_display()


class ProfessionalLicense(models.Model):
    STATE_CHOICES = (
        ('AL', 'Alabama'),
        ('AK', 'Alaska'),
        ('AZ', 'Arizona'),
        ('AR', 'Arkansas'),
        ('CA', 'California'),
        ('CO', 'Colorado'),
        ('CT', 'Connecticut'),
        ('DE', 'Delaware'),
        ('FL', 'Florida'),
        ('GA', 'Georgia'),
        ('HI', 'Hawaii'),
        ('ID', 'Idaho'),
        ('IL', 'Illinois'),
        ('IN', 'Indiana'),
        ('IA', 'Iowa'),
        ('KS', 'Kansas'),
        ('KY', 'Kentucky'),
        ('LA', 'Louisiana'),
        ('ME', 'Maine'),
        ('MD', 'Maryland'),
        ('MA', 'Massachusetts'),
        ('MI', 'Michigan'),
        ('MN', 'Minnesota'),
        ('MS', 'Mississippi'),
        ('MO', 'Missouri'),
        ('MT', 'Montana'),
        ('NE', 'Nebraska'),
        ('NV', 'Nevada'),
        ('NH', 'New Hampshire'),
        ('NJ', 'New Jersey'),
        ('NM', 'New Mexico'),
        ('NY', 'New York'),
        ('NC', 'North Carolina'),
        ('ND', 'North Dakota'),
        ('OH', 'Ohio'),
        ('OK', 'Oklahoma'),
        ('OR', 'Oregon'),
        ('PA', 'Pennsylvania'),
        ('RI', 'Rhode Island'),
        ('SC', 'South Carolina'),
        ('SD', 'South Dakota'),
        ('TN', 'Tennessee'),
        ('TX', 'Texas'),
        ('UT', 'Utah'),
        ('VT', 'Vermont'),
        ('VA', 'Virginia'),
        ('WA', 'Washington'),
        ('WV', 'West Virginia'),
        ('WI', 'Wisconsin'),
        ('WY', 'Wyoming'),
        ('PR', 'Puerto Rico'),
    )

    professional = models.ForeignKey(Professional, on_delete=models.CASCADE, related_name='licenses')
    license = models.ForeignKey(License, on_delete=models.CASCADE)
    license_number = models.CharField(max_length=50)
    expiration_date = models.DateField(null=True, blank=True)
    issued_state = models.CharField(max_length=2, choices=STATE_CHOICES)
    issued_date = models.DateField(null=True, blank=True)
    is_verified = models.BooleanField(default=False)

    # Potential Future Fields
    # verification_date = models.DateField(null=True, blank=True)
    # verification_source = models.CharField(max_length=255, blank=True)
    # verification_document = models.FileField(upload_to='verification_documents/', null=True, blank=True)
    # status = models.CharField(max_length=50, blank=True)
    # status_date = models.DateField(null=True, blank=True)
    # license_image = models.ImageField(upload_to='license_images/', null=True, blank=True)
    # license_url = models.URLField(blank=True)
    # license_number_verified = models.BooleanField(default=False)
    # license_number_verification_date = models.DateField(null=True, blank=True)
    # license_number_verification_source = models.CharField(max_length=255, blank=True)
    # license_number_verification_document = models.FileField(upload_to='license_number_verification_documents/', null=True, blank=True)

    class Meta:
        unique_together = ('professional', 'license', 'issued_state')

    def __str__(self):
        return f"{self.license.get_license_type_display()} ({self.state}) - {self.license_number} ({self.professional})"


class ProfessionalSpecialty(models.Model):
    professional = models.ForeignKey(Professional, on_delete=models.CASCADE, related_name='specialties')
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    description = models.TextField(blank=True)

    class Meta:
        verbose_name_plural = "Professional Specialties"

    def __str__(self):
        return f"{self.professional} - {self.category}"

