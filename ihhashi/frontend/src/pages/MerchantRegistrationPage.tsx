import { useState, useRef } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { 
  ArrowLeft, 
  Store, 
  Upload, 
  MapPin, 
  FileText, 
  CreditCard,
  CheckCircle,
  Loader2,
  AlertCircle,
  Building2,
  User,
  Briefcase,
  Shield
} from 'lucide-react'
import { useAuth } from '../App'

interface FormData {
  // Business Details
  businessName: string
  businessType: string
  description: string
  phone: string
  email: string
  
  // Address
  streetAddress: string
  city: string
  province: string
  postalCode: string
  
  // Bank Details
  accountHolder: string
  bankName: string
  accountNumber: string
  branchCode: string
  accountType: 'cheque' | 'savings' | 'business'
  
  // Documents
  idDocument: File | null
  businessRegistration: File | null
  proofOfAddress: File | null
  bankStatement: File | null
  
  // Terms
  acceptTerms: boolean
}

const businessTypes = [
  'Restaurant',
  'Fast Food',
  'Grocery Store',
  'Bakery',
  'Butchery',
  'Cafe',
  'Convenience Store',
  'Other'
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

export function MerchantRegistrationPage() {
  void useNavigate() // Reserved for future navigation
  const { isAuthenticated } = useAuth()
  const [step, setStep] = useState(1)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState(false)

  const [formData, setFormData] = useState<FormData>({
    businessName: '',
    businessType: '',
    description: '',
    phone: '',
    email: '',
    streetAddress: '',
    city: '',
    province: '',
    postalCode: '',
    accountHolder: '',
    bankName: '',
    accountNumber: '',
    branchCode: '',
    accountType: 'cheque',
    idDocument: null,
    businessRegistration: null,
    proofOfAddress: null,
    bankStatement: null,
    acceptTerms: false,
  })

  const fileInputRefs = {
    id: useRef<HTMLInputElement>(null),
    business: useRef<HTMLInputElement>(null),
    address: useRef<HTMLInputElement>(null),
    bank: useRef<HTMLInputElement>(null),
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
        if (!formData.businessName || !formData.businessType || !formData.phone) {
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
        if (!formData.accountHolder || !formData.bankName || !formData.accountNumber) {
          setError('Please fill in all bank details')
          return false
        }
        break
      case 4:
        if (!formData.idDocument || !formData.proofOfAddress) {
          setError('Please upload required documents')
          return false
        }
        break
      case 5:
        if (!formData.acceptTerms) {
          setError('Please accept the terms and conditions')
          return false
        }
        break
    }
    return true
  }

  const handleNext = () => {
    if (validateStep()) {
      setStep(prev => Math.min(prev + 1, 5))
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
        <h2 className="text-2xl font-bold text-gray-800 mb-2">Application Submitted!</h2>
        <p className="text-gray-500 mb-2 max-w-sm">
          Thank you for registering with iHhashi. Your application is under review.
        </p>
        <div className="bg-blue-50 border border-blue-200 rounded-xl px-4 py-3 mb-6">
          <p className="text-sm text-blue-700">
            <Shield className="w-4 h-4 inline mr-1" />
            Blue Horse verification typically takes 2-3 business days
          </p>
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
    <div className="flex items-center justify-center gap-2 mb-6">
      {[1, 2, 3, 4, 5].map((s) => (
        <div key={s} className="flex items-center">
          <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold transition ${
            s === step 
              ? 'bg-[#FF6B35] text-white' 
              : s < step 
                ? 'bg-green-500 text-white' 
                : 'bg-gray-200 text-gray-500'
          }`}>
            {s < step ? <CheckCircle className="w-5 h-5" /> : s}
          </div>
          {s < 5 && (
            <div className={`w-8 h-0.5 ${s < step ? 'bg-green-500' : 'bg-gray-200'}`} />
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
                <Store className="w-8 h-8 text-[#FF6B35]" />
              </div>
              <h2 className="text-xl font-bold text-gray-800">Business Details</h2>
              <p className="text-sm text-gray-500">Tell us about your business</p>
            </div>

            <div>
              <label className="text-sm font-medium text-gray-700 block mb-1">
                Business Name <span className="text-red-500">*</span>
              </label>
              <input
                name="businessName"
                type="text"
                placeholder="e.g. Nkosi's Kitchen"
                value={formData.businessName}
                onChange={handleInputChange}
                className="w-full border border-gray-200 rounded-xl px-4 py-3 outline-none focus:border-[#FF6B35] focus:ring-2 focus:ring-[#FF6B35]/20"
              />
            </div>

            <div>
              <label className="text-sm font-medium text-gray-700 block mb-1">
                Business Type <span className="text-red-500">*</span>
              </label>
              <select
                name="businessType"
                value={formData.businessType}
                onChange={handleInputChange}
                className="w-full border border-gray-200 rounded-xl px-4 py-3 outline-none focus:border-[#FF6B35] focus:ring-2 focus:ring-[#FF6B35]/20 bg-white"
              >
                <option value="">Select business type</option>
                {businessTypes.map(type => (
                  <option key={type} value={type}>{type}</option>
                ))}
              </select>
            </div>

            <div>
              <label className="text-sm font-medium text-gray-700 block mb-1">Description</label>
              <textarea
                name="description"
                placeholder="Tell customers about your business..."
                value={formData.description}
                onChange={handleInputChange}
                rows={3}
                className="w-full border border-gray-200 rounded-xl px-4 py-3 outline-none focus:border-[#FF6B35] focus:ring-2 focus:ring-[#FF6B35]/20 resize-none"
              />
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-sm font-medium text-gray-700 block mb-1">
                  Phone <span className="text-red-500">*</span>
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
                  placeholder="business@email.com"
                  value={formData.email}
                  onChange={handleInputChange}
                  className="w-full border border-gray-200 rounded-xl px-4 py-3 outline-none focus:border-[#FF6B35] focus:ring-2 focus:ring-[#FF6B35]/20"
                />
              </div>
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
              <h2 className="text-xl font-bold text-gray-800">Business Address</h2>
              <p className="text-sm text-gray-500">Where is your business located?</p>
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
                <label className="text-sm font-medium text-gray-700 block mb-1">
                  Postal Code
                </label>
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
                <CreditCard className="w-8 h-8 text-[#FF6B35]" />
              </div>
              <h2 className="text-xl font-bold text-gray-800">Bank Details</h2>
              <p className="text-sm text-gray-500">For receiving payouts</p>
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

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-sm font-medium text-gray-700 block mb-1">Branch Code</label>
                <input
                  name="branchCode"
                  type="text"
                  placeholder="e.g. 251705"
                  value={formData.branchCode}
                  onChange={handleInputChange}
                  className="w-full border border-gray-200 rounded-xl px-4 py-3 outline-none focus:border-[#FF6B35] focus:ring-2 focus:ring-[#FF6B35]/20"
                />
              </div>
              <div>
                <label className="text-sm font-medium text-gray-700 block mb-1">Account Type</label>
                <select
                  name="accountType"
                  value={formData.accountType}
                  onChange={handleInputChange}
                  className="w-full border border-gray-200 rounded-xl px-4 py-3 outline-none focus:border-[#FF6B35] focus:ring-2 focus:ring-[#FF6B35]/20 bg-white"
                >
                  <option value="cheque">Cheque</option>
                  <option value="savings">Savings</option>
                  <option value="business">Business</option>
                </select>
              </div>
            </div>
          </div>
        )

      case 4:
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

            {/* Business Registration */}
            <div className="border border-gray-200 rounded-xl p-4">
              <div className="flex items-start gap-3">
                <div className="w-10 h-10 bg-purple-100 rounded-lg flex items-center justify-center flex-shrink-0">
                  <Building2 className="w-5 h-5 text-purple-600" />
                </div>
                <div className="flex-1">
                  <h3 className="font-medium text-sm">Business Registration</h3>
                  <p className="text-xs text-gray-500 mb-2">CIPC certificate or similar</p>
                  {formData.businessRegistration ? (
                    <div className="flex items-center gap-2 text-sm text-green-600">
                      <CheckCircle className="w-4 h-4" />
                      <span className="truncate">{formData.businessRegistration.name}</span>
                      <button 
                        onClick={() => handleFileChange('businessRegistration', null)}
                        className="text-red-500 text-xs"
                      >
                        Remove
                      </button>
                    </div>
                  ) : (
                    <button
                      onClick={() => fileInputRefs.business.current?.click()}
                      className="flex items-center gap-2 text-sm text-[#FF6B35] font-medium"
                    >
                      <Upload className="w-4 h-4" />
                      Upload Document
                    </button>
                  )}
                  <input
                    ref={fileInputRefs.business}
                    type="file"
                    accept=".pdf,.jpg,.jpeg,.png"
                    onChange={(e) => handleFileChange('businessRegistration', e.target.files?.[0] || null)}
                    className="hidden"
                  />
                </div>
              </div>
            </div>

            {/* Proof of Address */}
            <div className="border border-gray-200 rounded-xl p-4">
              <div className="flex items-start gap-3">
                <div className="w-10 h-10 bg-green-100 rounded-lg flex items-center justify-center flex-shrink-0">
                  <MapPin className="w-5 h-5 text-green-600" />
                </div>
                <div className="flex-1">
                  <h3 className="font-medium text-sm">Proof of Address <span className="text-red-500">*</span></h3>
                  <p className="text-xs text-gray-500 mb-2">Utility bill or lease agreement (not older than 3 months)</p>
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

            {/* Bank Statement */}
            <div className="border border-gray-200 rounded-xl p-4">
              <div className="flex items-start gap-3">
                <div className="w-10 h-10 bg-yellow-100 rounded-lg flex items-center justify-center flex-shrink-0">
                  <Briefcase className="w-5 h-5 text-yellow-600" />
                </div>
                <div className="flex-1">
                  <h3 className="font-medium text-sm">Bank Statement</h3>
                  <p className="text-xs text-gray-500 mb-2">Last 3 months (optional but recommended)</p>
                  {formData.bankStatement ? (
                    <div className="flex items-center gap-2 text-sm text-green-600">
                      <CheckCircle className="w-4 h-4" />
                      <span className="truncate">{formData.bankStatement.name}</span>
                      <button 
                        onClick={() => handleFileChange('bankStatement', null)}
                        className="text-red-500 text-xs"
                      >
                        Remove
                      </button>
                    </div>
                  ) : (
                    <button
                      onClick={() => fileInputRefs.bank.current?.click()}
                      className="flex items-center gap-2 text-sm text-[#FF6B35] font-medium"
                    >
                      <Upload className="w-4 h-4" />
                      Upload Document
                    </button>
                  )}
                  <input
                    ref={fileInputRefs.bank}
                    type="file"
                    accept=".pdf,.jpg,.jpeg,.png"
                    onChange={(e) => handleFileChange('bankStatement', e.target.files?.[0] || null)}
                    className="hidden"
                  />
                </div>
              </div>
            </div>
          </div>
        )

      case 5:
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
              <h3 className="font-medium text-gray-800">iHhashi Merchant Agreement</h3>
              <p>By registering as a merchant on iHhashi, you agree to:</p>
              <ul className="list-disc pl-5 space-y-1">
                <li>Maintain food safety and hygiene standards</li>
                <li>Accept orders within 5 minutes during business hours</li>
                <li>Prepare orders within the stated time</li>
                <li>Keep menu items and prices accurate and up-to-date</li>
                <li>Pay commission fees as specified in the fee schedule</li>
                <li>Maintain valid business licenses and permits</li>
                <li>Respond to customer inquiries within 24 hours</li>
                <li>Accept the Blue Horse verification process</li>
              </ul>
              <p className="text-xs text-gray-400 mt-2">
                Full terms available at ihhashi.com/terms
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
                I agree to the iHhashi Merchant Terms and Conditions, Privacy Policy, and Blue Horse verification process.
              </span>
            </label>

            <div className="bg-blue-50 border border-blue-200 rounded-xl p-3">
              <div className="flex items-start gap-2">
                <Shield className="w-5 h-5 text-blue-600 flex-shrink-0 mt-0.5" />
                <div>
                  <p className="text-sm font-medium text-blue-800">Blue Horse Verification</p>
                  <p className="text-xs text-blue-600">
                    Your documents will be reviewed within 2-3 business days. You'll receive an email once verified.
                  </p>
                </div>
              </div>
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
          <h1 className="text-lg font-semibold ml-2">Become a Merchant</h1>
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
          {step < 5 ? (
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
          Step {step} of 5
        </p>
      </div>
    </div>
  )
}
