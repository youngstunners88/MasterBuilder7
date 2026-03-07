import { useState, useRef } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { 
  ArrowLeft, 
  Bike, 
  Upload, 
  MapPin, 
  FileText, 

  CheckCircle,
  Loader2,
  AlertCircle,
  User,
  Car,
  Truck,
  Footprints,
  Wallet,
  Shield,
  Clock,
  Star
} from 'lucide-react'
import { useAuth } from '../App'

interface FormData {
  // Personal Details
  firstName: string
  lastName: string
  phone: string
  email: string
  idNumber: string
  dateOfBirth: string
  
  // Address
  streetAddress: string
  city: string
  province: string
  postalCode: string
  
  // Vehicle Information
  transportType: string
  vehicleMake: string
  vehicleModel: string
  vehicleColor: string
  vehicleYear: string
  licensePlate: string
  
  // Bank Details
  accountHolder: string
  bankName: string
  accountNumber: string
  
  // Documents
  idDocument: File | null
  driversLicense: File | null
  vehicleRegistration: File | null
  proofOfAddress: File | null
  
  // Terms
  acceptTerms: boolean
  backgroundCheck: boolean
}

const transportTypes = [
  { id: 'car', label: 'Car', icon: Car, description: 'Standard vehicle' },
  { id: 'motorcycle', label: 'Motorcycle', icon: Bike, description: 'Fast delivery' },
  { id: 'scooter', label: 'Scooter', icon: Bike, description: 'Easy parking' },
  { id: 'bicycle', label: 'Bicycle', icon: Bike, description: 'Eco-friendly' },
  { id: 'foot', label: 'On Foot', icon: Footprints, description: 'Short distances' },
  { id: 'wheelchair', label: 'Wheelchair', icon: Truck, description: 'Accessible' },
  { id: 'running', label: 'Running', icon: Footprints, description: 'Fitness delivery' },
  { id: 'rollerblade', label: 'Rollerblade', icon: Bike, description: 'Quick & fun' },
]

const provinces = [
  'Gauteng',
  'Western Cape',
  'KwaZulu-Natal',
  'Eastern Cape',
  'Free State',
  'Mpumalanga',
  'North West',
  'Limpopo',
  'Northern Cape'
]

const banks = [
  'FNB (First National Bank)',
  'Standard Bank',
  'ABSA',
  'Nedbank',
  'Capitec',
  'Discovery Bank',
  'TymeBank',
  'Investec',
  'African Bank'
]

export function DriverRegistrationPage() {
  void useNavigate() // Reserved for future navigation
  const { isAuthenticated } = useAuth()
  const [step, setStep] = useState(1)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState(false)

  const [formData, setFormData] = useState<FormData>({
    firstName: '',
    lastName: '',
    phone: '',
    email: '',
    idNumber: '',
    dateOfBirth: '',
    streetAddress: '',
    city: '',
    province: '',
    postalCode: '',
    transportType: '',
    vehicleMake: '',
    vehicleModel: '',
    vehicleColor: '',
    vehicleYear: '',
    licensePlate: '',
    accountHolder: '',
    bankName: '',
    accountNumber: '',
    idDocument: null,
    driversLicense: null,
    vehicleRegistration: null,
    proofOfAddress: null,
    acceptTerms: false,
    backgroundCheck: false,
  })

  const fileInputRefs = {
    id: useRef<HTMLInputElement>(null),
    license: useRef<HTMLInputElement>(null),
    registration: useRef<HTMLInputElement>(null),
    address: useRef<HTMLInputElement>(null),
  }

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) => {
    const { name, value, type } = e.target
    setFormData(prev => ({
      ...prev,
      [name]: type === 'checkbox' ? (e.target as HTMLInputElement).checked : value
    }))
    setError('')
  }

  const handleFileChange = (field: keyof FormData, file: File | null) => {
    setFormData(prev => ({ ...prev, [field]: file }))
    setError('')
  }

  const validateStep = () => {
    switch (step) {
      case 1:
        if (!formData.firstName || !formData.lastName || !formData.phone || !formData.idNumber) {
          setError('Please fill in all required fields')
          return false
        }
        break
      case 2:
        if (!formData.streetAddress || !formData.city || !formData.province) {
          setError('Please fill in all address fields')
          return false
        }
        break
      case 3:
        if (!formData.transportType) {
          setError('Please select your transport type')
          return false
        }
        if (formData.transportType !== 'foot' && formData.transportType !== 'running') {
          if (!formData.licensePlate) {
            setError('Please enter your license plate number')
            return false
          }
        }
        break
      case 4:
        if (!formData.accountHolder || !formData.bankName || !formData.accountNumber) {
          setError('Please fill in all bank details')
          return false
        }
        break
      case 5:
        if (!formData.idDocument || !formData.driversLicense || !formData.proofOfAddress) {
          setError('Please upload all required documents')
          return false
        }
        break
      case 6:
        if (!formData.acceptTerms || !formData.backgroundCheck) {
          setError('Please accept all terms to continue')
          return false
        }
        break
    }
    return true
  }

  const handleNext = () => {
    if (validateStep()) {
      setStep(prev => Math.min(prev + 1, 6))
      setError('')
    }
  }

  const handleBack = () => {
    setStep(prev => Math.max(prev - 1, 1))
    setError('')
  }

  const handleSubmit = async () => {
    if (!validateStep()) return

    setLoading(true)
    setError('')

    try {
      // Simulate API call
      await new Promise(resolve => setTimeout(resolve, 2000))
      setSuccess(true)
    } catch (err: any) {
      setError(err.message || 'Registration failed. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  if (success) {
    return (
      <div className="min-h-screen bg-gray-50 flex flex-col items-center justify-center p-6 text-center">
        <div className="w-20 h-20 bg-green-100 rounded-full flex items-center justify-center mb-6">
          <CheckCircle className="w-10 h-10 text-green-500" />
        </div>
        <h2 className="text-2xl font-bold text-gray-800 mb-2">Welcome to iHhashi!</h2>
        <p className="text-gray-500 mb-2 max-w-sm">
          Your application has been submitted successfully.
        </p>
        <div className="bg-blue-50 border border-blue-200 rounded-xl px-4 py-3 mb-6">
          <p className="text-sm text-blue-700">
            <Shield className="w-4 h-4 inline mr-1" />
            Blue Horse verification typically takes 1-2 business days
          </p>
        </div>
        <div className="bg-yellow-50 border border-yellow-200 rounded-xl px-4 py-3 mb-6">
          <div className="flex items-start gap-2">
            <Clock className="w-4 h-4 text-yellow-600 flex-shrink-0 mt-0.5" />
            <div className="text-left">
              <p className="text-sm font-medium text-yellow-800">What happens next?</p>
              <ul className="text-xs text-yellow-700 mt-1 space-y-0.5">
                <li>• Document verification (1-2 days)</li>
                <li>• Background check</li>
                <li>• Account activation email</li>
                <li>• Start earning!</li>
              </ul>
            </div>
          </div>
        </div>
        <div className="space-y-3 w-full max-w-xs">
          <Link 
            to="/" 
            className="block w-full bg-[#FF6B35] text-white font-semibold py-3 rounded-xl hover:bg-[#e55a25] transition"
          >
            Back to Home
          </Link>
          {!isAuthenticated && (
            <Link 
              to="/auth" 
              className="block w-full bg-white border border-gray-200 text-gray-700 font-semibold py-3 rounded-xl hover:bg-gray-50 transition"
            >
              Create Account
            </Link>
          )}
        </div>
      </div>
    )
  }

  const renderStepIndicator = () => (
    <div className="flex items-center justify-center gap-1 mb-6 overflow-x-auto">
      {[1, 2, 3, 4, 5, 6].map((s) => (
        <div key={s} className="flex items-center flex-shrink-0">
          <div className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold transition ${
            s === step 
              ? 'bg-[#FF6B35] text-white' 
              : s < step 
                ? 'bg-green-500 text-white' 
                : 'bg-gray-200 text-gray-500'
          }`}>
            {s < step ? <CheckCircle className="w-4 h-4" /> : s}
          </div>
          {s < 6 && (
            <div className={`w-4 h-0.5 ${s < step ? 'bg-green-500' : 'bg-gray-200'}`} />
          )}
        </div>
      ))}
    </div>
  )

  const renderStep = () => {
    switch (step) {
      case 1:
        return (
          <div className="space-y-4">
            <div className="text-center mb-6">
              <div className="w-16 h-16 bg-[#FF6B35]/10 rounded-full flex items-center justify-center mx-auto mb-3">
                <User className="w-8 h-8 text-[#FF6B35]" />
              </div>
              <h2 className="text-xl font-bold text-gray-800">Personal Details</h2>
              <p className="text-sm text-gray-500">Tell us about yourself</p>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-sm font-medium text-gray-700 block mb-1">
                  First Name <span className="text-red-500">*</span>
                </label>
                <input
                  name="firstName"
                  type="text"
                  placeholder="Thandi"
                  value={formData.firstName}
                  onChange={handleInputChange}
                  className="w-full border border-gray-200 rounded-xl px-4 py-3 outline-none focus:border-[#FF6B35] focus:ring-2 focus:ring-[#FF6B35]/20"
                />
              </div>
              <div>
                <label className="text-sm font-medium text-gray-700 block mb-1">
                  Last Name <span className="text-red-500">*</span>
                </label>
                <input
                  name="lastName"
                  type="text"
                  placeholder="Nkosi"
                  value={formData.lastName}
                  onChange={handleInputChange}
                  className="w-full border border-gray-200 rounded-xl px-4 py-3 outline-none focus:border-[#FF6B35] focus:ring-2 focus:ring-[#FF6B35]/20"
                />
              </div>
            </div>

            <div>
              <label className="text-sm font-medium text-gray-700 block mb-1">
                Phone Number <span className="text-red-500">*</span>
              </label>
              <div className="flex items-center border border-gray-200 rounded-xl overflow-hidden">
                <span className="px-3 py-3 bg-gray-50 text-gray-600 text-sm border-r border-gray-200">+27</span>
                <input
                  name="phone"
                  type="tel"
                  placeholder="821234567"
                  value={formData.phone}
                  onChange={handleInputChange}
                  className="flex-1 px-3 py-3 outline-none"
                  maxLength={9}
                />
              </div>
            </div>

            <div>
              <label className="text-sm font-medium text-gray-700 block mb-1">Email</label>
              <input
                name="email"
                type="email"
                placeholder="you@example.com"
                value={formData.email}
                onChange={handleInputChange}
                className="w-full border border-gray-200 rounded-xl px-4 py-3 outline-none focus:border-[#FF6B35] focus:ring-2 focus:ring-[#FF6B35]/20"
              />
            </div>

            <div>
              <label className="text-sm font-medium text-gray-700 block mb-1">
                South African ID Number <span className="text-red-500">*</span>
              </label>
              <input
                name="idNumber"
                type="text"
                placeholder="13-digit ID number"
                value={formData.idNumber}
                onChange={handleInputChange}
                className="w-full border border-gray-200 rounded-xl px-4 py-3 outline-none focus:border-[#FF6B35] focus:ring-2 focus:ring-[#FF6B35]/20"
                maxLength={13}
              />
            </div>

            <div>
              <label className="text-sm font-medium text-gray-700 block mb-1">Date of Birth</label>
              <input
                name="dateOfBirth"
                type="date"
                value={formData.dateOfBirth}
                onChange={handleInputChange}
                className="w-full border border-gray-200 rounded-xl px-4 py-3 outline-none focus:border-[#FF6B35] focus:ring-2 focus:ring-[#FF6B35]/20"
              />
            </div>
          </div>
        )

      case 2:
        return (
          <div className="space-y-4">
            <div className="text-center mb-6">
              <div className="w-16 h-16 bg-[#FF6B35]/10 rounded-full flex items-center justify-center mx-auto mb-3">
                <MapPin className="w-8 h-8 text-[#FF6B35]" />
              </div>
              <h2 className="text-xl font-bold text-gray-800">Your Address</h2>
              <p className="text-sm text-gray-500">Where do you live?</p>
            </div>

            <div>
              <label className="text-sm font-medium text-gray-700 block mb-1">
                Street Address <span className="text-red-500">*</span>
              </label>
              <input
                name="streetAddress"
                type="text"
                placeholder="123 Main Street"
                value={formData.streetAddress}
                onChange={handleInputChange}
                className="w-full border border-gray-200 rounded-xl px-4 py-3 outline-none focus:border-[#FF6B35] focus:ring-2 focus:ring-[#FF6B35]/20"
              />
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-sm font-medium text-gray-700 block mb-1">
                  City <span className="text-red-500">*</span>
                </label>
                <input
                  name="city"
                  type="text"
                  placeholder="Johannesburg"
                  value={formData.city}
                  onChange={handleInputChange}
                  className="w-full border border-gray-200 rounded-xl px-4 py-3 outline-none focus:border-[#FF6B35] focus:ring-2 focus:ring-[#FF6B35]/20"
                />
              </div>
              <div>
                <label className="text-sm font-medium text-gray-700 block mb-1">Postal Code</label>
                <input
                  name="postalCode"
                  type="text"
                  placeholder="2000"
                  value={formData.postalCode}
                  onChange={handleInputChange}
                  className="w-full border border-gray-200 rounded-xl px-4 py-3 outline-none focus:border-[#FF6B35] focus:ring-2 focus:ring-[#FF6B35]/20"
                />
              </div>
            </div>

            <div>
              <label className="text-sm font-medium text-gray-700 block mb-1">
                Province <span className="text-red-500">*</span>
              </label>
              <select
                name="province"
                value={formData.province}
                onChange={handleInputChange}
                className="w-full border border-gray-200 rounded-xl px-4 py-3 outline-none focus:border-[#FF6B35] focus:ring-2 focus:ring-[#FF6B35]/20 bg-white"
              >
                <option value="">Select province</option>
                {provinces.map(province => (
                  <option key={province} value={province}>{province}</option>
                ))}
              </select>
            </div>
          </div>
        )

      case 3:
        return (
          <div className="space-y-4">
            <div className="text-center mb-6">
              <div className="w-16 h-16 bg-[#FF6B35]/10 rounded-full flex items-center justify-center mx-auto mb-3">
                <Bike className="w-8 h-8 text-[#FF6B35]" />
              </div>
              <h2 className="text-xl font-bold text-gray-800">Transport Type</h2>
              <p className="text-sm text-gray-500">How will you deliver?</p>
            </div>

            <div className="grid grid-cols-2 gap-3">
              {transportTypes.map((type) => {
                const Icon = type.icon
                return (
                  <button
                    key={type.id}
                    onClick={() => setFormData(prev => ({ ...prev, transportType: type.id }))}
                    className={`p-4 rounded-xl border-2 text-left transition ${
                      formData.transportType === type.id
                        ? 'border-[#FF6B35] bg-orange-50'
                        : 'border-gray-200 hover:border-gray-300'
                    }`}
                  >
                    <Icon className={`w-6 h-6 mb-2 ${
                      formData.transportType === type.id ? 'text-[#FF6B35]' : 'text-gray-400'
                    }`} />
                    <p className={`font-medium text-sm ${
                      formData.transportType === type.id ? 'text-[#FF6B35]' : 'text-gray-700'
                    }`}>
                      {type.label}
                    </p>
                    <p className="text-xs text-gray-500">{type.description}</p>
                  </button>
                )
              })}
            </div>

            {formData.transportType && formData.transportType !== 'foot' && formData.transportType !== 'running' && (
              <div className="mt-4 space-y-4 border-t border-gray-100 pt-4">
                <h3 className="font-medium text-gray-800">Vehicle Details</h3>
                
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="text-sm font-medium text-gray-700 block mb-1">Make</label>
                    <input
                      name="vehicleMake"
                      type="text"
                      placeholder="e.g. Toyota"
                      value={formData.vehicleMake}
                      onChange={handleInputChange}
                      className="w-full border border-gray-200 rounded-xl px-4 py-3 outline-none focus:border-[#FF6B35] focus:ring-2 focus:ring-[#FF6B35]/20"
                    />
                  </div>
                  <div>
                    <label className="text-sm font-medium text-gray-700 block mb-1">Model</label>
                    <input
                      name="vehicleModel"
                      type="text"
                      placeholder="e.g. Corolla"
                      value={formData.vehicleModel}
                      onChange={handleInputChange}
                      className="w-full border border-gray-200 rounded-xl px-4 py-3 outline-none focus:border-[#FF6B35] focus:ring-2 focus:ring-[#FF6B35]/20"
                    />
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="text-sm font-medium text-gray-700 block mb-1">Color</label>
                    <input
                      name="vehicleColor"
                      type="text"
                      placeholder="e.g. Silver"
                      value={formData.vehicleColor}
                      onChange={handleInputChange}
                      className="w-full border border-gray-200 rounded-xl px-4 py-3 outline-none focus:border-[#FF6B35] focus:ring-2 focus:ring-[#FF6B35]/20"
                    />
                  </div>
                  <div>
                    <label className="text-sm font-medium text-gray-700 block mb-1">Year</label>
                    <input
                      name="vehicleYear"
                      type="text"
                      placeholder="e.g. 2020"
                      value={formData.vehicleYear}
                      onChange={handleInputChange}
                      className="w-full border border-gray-200 rounded-xl px-4 py-3 outline-none focus:border-[#FF6B35] focus:ring-2 focus:ring-[#FF6B35]/20"
                    />
                  </div>
                </div>

                <div>
                  <label className="text-sm font-medium text-gray-700 block mb-1">
                    License Plate <span className="text-red-500">*</span>
                  </label>
                  <input
                    name="licensePlate"
                    type="text"
                    placeholder="e.g. GP 123-456"
                    value={formData.licensePlate}
                    onChange={handleInputChange}
                    className="w-full border border-gray-200 rounded-xl px-4 py-3 outline-none focus:border-[#FF6B35] focus:ring-2 focus:ring-[#FF6B35]/20"
                  />
                </div>
              </div>
            )}
          </div>
        )

      case 4:
        return (
          <div className="space-y-4">
            <div className="text-center mb-6">
              <div className="w-16 h-16 bg-[#FF6B35]/10 rounded-full flex items-center justify-center mx-auto mb-3">
                <Wallet className="w-8 h-8 text-[#FF6B35]" />
              </div>
              <h2 className="text-xl font-bold text-gray-800">Bank Details</h2>
              <p className="text-sm text-gray-500">For weekly payouts</p>
            </div>

            <div className="bg-green-50 border border-green-200 rounded-xl p-3 mb-4">
              <div className="flex items-start gap-2">
                <Clock className="w-5 h-5 text-green-600 flex-shrink-0 mt-0.5" />
                <div>
                  <p className="text-sm font-medium text-green-800">Payout Schedule</p>
                  <p className="text-xs text-green-600">
                    Get paid every Sunday at 11:11 AM. Minimum payout: R100.
                  </p>
                </div>
              </div>
            </div>

            <div>
              <label className="text-sm font-medium text-gray-700 block mb-1">
                Account Holder Name <span className="text-red-500">*</span>
              </label>
              <input
                name="accountHolder"
                type="text"
                placeholder="Full name on account"
                value={formData.accountHolder}
                onChange={handleInputChange}
                className="w-full border border-gray-200 rounded-xl px-4 py-3 outline-none focus:border-[#FF6B35] focus:ring-2 focus:ring-[#FF6B35]/20"
              />
            </div>

            <div>
              <label className="text-sm font-medium text-gray-700 block mb-1">
                Bank <span className="text-red-500">*</span>
              </label>
              <select
                name="bankName"
                value={formData.bankName}
                onChange={handleInputChange}
                className="w-full border border-gray-200 rounded-xl px-4 py-3 outline-none focus:border-[#FF6B35] focus:ring-2 focus:ring-[#FF6B35]/20 bg-white"
              >
                <option value="">Select your bank</option>
                {banks.map(bank => (
                  <option key={bank} value={bank}>{bank}</option>
                ))}
              </select>
            </div>

            <div>
              <label className="text-sm font-medium text-gray-700 block mb-1">
                Account Number <span className="text-red-500">*</span>
              </label>
              <input
                name="accountNumber"
                type="text"
                placeholder="Enter account number"
                value={formData.accountNumber}
                onChange={handleInputChange}
                className="w-full border border-gray-200 rounded-xl px-4 py-3 outline-none focus:border-[#FF6B35] focus:ring-2 focus:ring-[#FF6B35]/20"
              />
            </div>
          </div>
        )

      case 5:
        return (
          <div className="space-y-4">
            <div className="text-center mb-6">
              <div className="w-16 h-16 bg-[#FF6B35]/10 rounded-full flex items-center justify-center mx-auto mb-3">
                <FileText className="w-8 h-8 text-[#FF6B35]" />
              </div>
              <h2 className="text-xl font-bold text-gray-800">Document Upload</h2>
              <p className="text-sm text-gray-500">For Blue Horse verification</p>
            </div>

            {/* ID Document */}
            <div className="border border-gray-200 rounded-xl p-4">
              <div className="flex items-start gap-3">
                <div className="w-10 h-10 bg-blue-100 rounded-lg flex items-center justify-center flex-shrink-0">
                  <User className="w-5 h-5 text-blue-600" />
                </div>
                <div className="flex-1">
                  <h3 className="font-medium text-sm">ID Document <span className="text-red-500">*</span></h3>
                  <p className="text-xs text-gray-500 mb-2">South African ID or Passport</p>
                  {formData.idDocument ? (
                    <div className="flex items-center gap-2 text-sm text-green-600">
                      <CheckCircle className="w-4 h-4" />
                      <span className="truncate">{formData.idDocument.name}</span>
                      <button 
                        onClick={() => handleFileChange('idDocument', null)}
                        className="text-red-500 text-xs"
                      >
                        Remove
                      </button>
                    </div>
                  ) : (
                    <button
                      onClick={() => fileInputRefs.id.current?.click()}
                      className="flex items-center gap-2 text-sm text-[#FF6B35] font-medium"
                    >
                      <Upload className="w-4 h-4" />
                      Upload Document
                    </button>
                  )}
                  <input
                    ref={fileInputRefs.id}
                    type="file"
                    accept=".pdf,.jpg,.jpeg,.png"
                    onChange={(e) => handleFileChange('idDocument', e.target.files?.[0] || null)}
                    className="hidden"
                  />
                </div>
              </div>
            </div>

            {/* Driver's License */}
            <div className="border border-gray-200 rounded-xl p-4">
              <div className="flex items-start gap-3">
                <div className="w-10 h-10 bg-purple-100 rounded-lg flex items-center justify-center flex-shrink-0">
                  <Car className="w-5 h-5 text-purple-600" />
                </div>
                <div className="flex-1">
                  <h3 className="font-medium text-sm">Driver's License <span className="text-red-500">*</span></h3>
                  <p className="text-xs text-gray-500 mb-2">Valid South African driver's license</p>
                  {formData.driversLicense ? (
                    <div className="flex items-center gap-2 text-sm text-green-600">
                      <CheckCircle className="w-4 h-4" />
                      <span className="truncate">{formData.driversLicense.name}</span>
                      <button 
                        onClick={() => handleFileChange('driversLicense', null)}
                        className="text-red-500 text-xs"
                      >
                        Remove
                      </button>
                    </div>
                  ) : (
                    <button
                      onClick={() => fileInputRefs.license.current?.click()}
                      className="flex items-center gap-2 text-sm text-[#FF6B35] font-medium"
                    >
                      <Upload className="w-4 h-4" />
                      Upload Document
                    </button>
                  )}
                  <input
                    ref={fileInputRefs.license}
                    type="file"
                    accept=".pdf,.jpg,.jpeg,.png"
                    onChange={(e) => handleFileChange('driversLicense', e.target.files?.[0] || null)}
                    className="hidden"
                  />
                </div>
              </div>
            </div>

            {/* Vehicle Registration */}
            {formData.transportType !== 'foot' && formData.transportType !== 'running' && formData.transportType !== 'wheelchair' && (
              <div className="border border-gray-200 rounded-xl p-4">
                <div className="flex items-start gap-3">
                  <div className="w-10 h-10 bg-green-100 rounded-lg flex items-center justify-center flex-shrink-0">
                    <Bike className="w-5 h-5 text-green-600" />
                  </div>
                  <div className="flex-1">
                    <h3 className="font-medium text-sm">Vehicle Registration</h3>
                    <p className="text-xs text-gray-500 mb-2">Vehicle registration certificate</p>
                    {formData.vehicleRegistration ? (
                      <div className="flex items-center gap-2 text-sm text-green-600">
                        <CheckCircle className="w-4 h-4" />
                        <span className="truncate">{formData.vehicleRegistration.name}</span>
                        <button 
                          onClick={() => handleFileChange('vehicleRegistration', null)}
                          className="text-red-500 text-xs"
                        >
                          Remove
                        </button>
                      </div>
                    ) : (
                      <button
                        onClick={() => fileInputRefs.registration.current?.click()}
                        className="flex items-center gap-2 text-sm text-[#FF6B35] font-medium"
                      >
                        <Upload className="w-4 h-4" />
                        Upload Document
                      </button>
                    )}
                    <input
                      ref={fileInputRefs.registration}
                      type="file"
                      accept=".pdf,.jpg,.jpeg,.png"
                      onChange={(e) => handleFileChange('vehicleRegistration', e.target.files?.[0] || null)}
                      className="hidden"
                    />
                  </div>
                </div>
              </div>
            )}

            {/* Proof of Address */}
            <div className="border border-gray-200 rounded-xl p-4">
              <div className="flex items-start gap-3">
                <div className="w-10 h-10 bg-yellow-100 rounded-lg flex items-center justify-center flex-shrink-0">
                  <MapPin className="w-5 h-5 text-yellow-600" />
                </div>
                <div className="flex-1">
                  <h3 className="font-medium text-sm">Proof of Address <span className="text-red-500">*</span></h3>
                  <p className="text-xs text-gray-500 mb-2">Utility bill or lease agreement</p>
                  {formData.proofOfAddress ? (
                    <div className="flex items-center gap-2 text-sm text-green-600">
                      <CheckCircle className="w-4 h-4" />
                      <span className="truncate">{formData.proofOfAddress.name}</span>
                      <button 
                        onClick={() => handleFileChange('proofOfAddress', null)}
                        className="text-red-500 text-xs"
                      >
                        Remove
                      </button>
                    </div>
                  ) : (
                    <button
                      onClick={() => fileInputRefs.address.current?.click()}
                      className="flex items-center gap-2 text-sm text-[#FF6B35] font-medium"
                    >
                      <Upload className="w-4 h-4" />
                      Upload Document
                    </button>
                  )}
                  <input
                    ref={fileInputRefs.address}
                    type="file"
                    accept=".pdf,.jpg,.jpeg,.png"
                    onChange={(e) => handleFileChange('proofOfAddress', e.target.files?.[0] || null)}
                    className="hidden"
                  />
                </div>
              </div>
            </div>
          </div>
        )

      case 6:
        return (
          <div className="space-y-4">
            <div className="text-center mb-6">
              <div className="w-16 h-16 bg-[#FF6B35]/10 rounded-full flex items-center justify-center mx-auto mb-3">
                <Shield className="w-8 h-8 text-[#FF6B35]" />
              </div>
              <h2 className="text-xl font-bold text-gray-800">Terms & Conditions</h2>
              <p className="text-sm text-gray-500">Review and accept to complete</p>
            </div>

            <div className="bg-gray-50 rounded-xl p-4 max-h-48 overflow-y-auto text-sm text-gray-600 space-y-3">
              <h3 className="font-medium text-gray-800">iHhashi Delivery Partner Agreement</h3>
              <p>By becoming a delivery partner, you agree to:</p>
              <ul className="list-disc pl-5 space-y-1">
                <li>Accept delivery requests promptly and professionally</li>
                <li>Deliver orders within the estimated time</li>
                <li>Maintain food safety and hygiene standards</li>
                <li>Follow all traffic laws and safety regulations</li>
                <li>Maintain a valid driver's license and vehicle registration</li>
                <li>Keep your vehicle in safe working condition</li>
                <li>Pass a background check</li>
                <li>Maintain professional communication with customers</li>
              </ul>
              <p className="text-xs text-gray-400 mt-2">
                Full terms available at ihhashi.com/driver-terms
              </p>
            </div>

            <label className="flex items-start gap-3 cursor-pointer">
              <input
                type="checkbox"
                name="acceptTerms"
                checked={formData.acceptTerms}
                onChange={handleInputChange}
                className="w-5 h-5 rounded border-gray-300 text-[#FF6B35] focus:ring-[#FF6B35] mt-0.5"
              />
              <span className="text-sm text-gray-600">
                I agree to the iHhashi Delivery Partner Terms and Conditions and Privacy Policy.
              </span>
            </label>

            <label className="flex items-start gap-3 cursor-pointer">
              <input
                type="checkbox"
                name="backgroundCheck"
                checked={formData.backgroundCheck}
                onChange={handleInputChange}
                className="w-5 h-5 rounded border-gray-300 text-[#FF6B35] focus:ring-[#FF6B35] mt-0.5"
              />
              <span className="text-sm text-gray-600">
                I consent to a background check as part of the Blue Horse verification process.
              </span>
            </label>

            <div className="bg-gradient-to-r from-primary/20 to-primary/10 rounded-xl p-4">
              <div className="flex items-center gap-2 mb-2">
                <Star className="w-5 h-5 text-[#FF6B35]" />
                <span className="font-medium text-gray-800">Why join iHhashi?</span>
              </div>
              <ul className="text-sm text-gray-600 space-y-1">
                <li>• Set your own schedule</li>
                <li>• Competitive earnings with weekly payouts</li>
                <li>• Inclusive - all transport types welcome</li>
                <li>• 100% of tips go to you</li>
                <li>• Blue Horse verified = higher earnings</li>
              </ul>
            </div>
          </div>
        )

      default:
        return null
    }
  }

  return (
    <div className="min-h-screen bg-gray-50 pb-8">
      {/* Header */}
      <header className="bg-white border-b border-gray-100 sticky top-0 z-10">
        <div className="max-w-lg mx-auto px-4 py-3 flex items-center">
          {step === 1 ? (
            <Link to="/" className="p-2 -ml-2">
              <ArrowLeft className="w-6 h-6" />
            </Link>
          ) : (
            <button onClick={handleBack} className="p-2 -ml-2">
              <ArrowLeft className="w-6 h-6" />
            </button>
          )}
          <h1 className="text-lg font-semibold ml-2">Become a Driver</h1>
        </div>
      </header>

      <div className="max-w-lg mx-auto px-4 py-6">
        {renderStepIndicator()}

        {error && (
          <div className="bg-red-50 border border-red-200 rounded-xl px-4 py-3 flex items-center gap-2 text-red-700 text-sm mb-4">
            <AlertCircle className="w-4 h-4 flex-shrink-0" />
            {error}
          </div>
        )}

        {renderStep()}

        <div className="mt-8">
          {step < 6 ? (
            <button
              onClick={handleNext}
              className="w-full bg-[#FF6B35] text-white font-bold py-4 rounded-xl hover:bg-[#e55a25] transition"
            >
              Continue
            </button>
          ) : (
            <button
              onClick={handleSubmit}
              disabled={loading}
              className="w-full bg-[#FF6B35] text-white font-bold py-4 rounded-xl hover:bg-[#e55a25] transition disabled:opacity-60 flex items-center justify-center gap-2"
            >
              {loading ? (
                <><Loader2 className="w-5 h-5 animate-spin" /> Submitting...</>
              ) : (
                'Submit Application'
              )}
            </button>
          )}
        </div>

        <p className="text-xs text-gray-400 text-center mt-4">
          Step {step} of 6
        </p>
      </div>
    </div>
  )
}
