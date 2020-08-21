#include <map>
#include <limits>
#include <math.h>
#include <string>
#include <vector>
#include <boost/python.hpp>
using namespace boost::python;

/*
 *  TODO:
 *  - Implement asset precisions flooring
 */

/*
 *  Converting Python iterables to C++ vectors
 */
// PyList<T> --> 1D vector <T>
template <typename T>
inline std::vector<T> to_1d_vector(const boost::python::object &iterable)
{
  return std::vector<T>(
      boost::python::stl_input_iterator<T>(iterable),
      boost::python::stl_input_iterator<T>());
}

// PyList<PyList<T>> --> 2D vector <T>
template <typename T>
inline std::vector<std::vector<T>> to_2d_vector(const boost::python::object &iterable)
{
  std::vector<boost::python::object> intermediate = to_1d_vector<boost::python::object>(iterable);
  std::vector<std::vector<T>> ending;
  for (unsigned short i = 0; i < intermediate.size(); i++)
  {
    ending.push_back(to_1d_vector<T>(*intermediate[i]));
  }
  return ending;
}

// 1D vector <T> --> PyList<T>
template <class T>
inline boost::python::list to_py_list(std::vector<T> vector)
{
  typename std::vector<T>::iterator iter;
  boost::python::list list;
  for (iter = vector.begin(); iter != vector.end(); ++iter)
  {
    list.append(*iter);
  }
  return list;
}

/*
 *  Trading pair wrapper
 */
struct Pair
{
public:
  Pair(std::string name)
  {
    this->symbol = name;
    this->timestamp = 0;
  };

  void update(double timestamp, std::vector<std::vector<double>> asks, std::vector<std::vector<double>> bids)
  {
    this->timestamp = timestamp;
    this->asks = asks;
    this->bids = bids;
  }

  double getTimestamp()
  {
    return this->timestamp;
  }

  std::vector<std::vector<double>> getAsks()
  {
    return this->asks;
  }

  std::vector<std::vector<double>> getBids()
  {
    return this->bids;
  }

private:
  std::string symbol;
  double timestamp;
  std::vector<std::vector<double>> asks;
  std::vector<std::vector<double>> bids;
};

/*
 *  Triangular relationship wrapper
 */
struct Relationship
{
public:
  Relationship(std::vector<std::string> pairs, std::vector<std::string> actions)
  {
    this->pairs = pairs;
    this->actions = actions;
  }

  std::vector<std::string> getPairs()
  {
    return this->pairs;
  }

  std::vector<std::string> getActions()
  {
    return this->actions;
  }

private:
  std::vector<std::string> pairs;
  std::vector<std::string> actions;
};

/*
 *  Main class
 */
struct ClassWithNoName
{
public:
  ClassWithNoName(double fee, boost::python::object quantityRange)
  {
    this->fee = fee;
    this->feeMultiplier = pow((100 - fee) / 100, 3);
    this->qtyRange = to_1d_vector<double>(quantityRange);
  }

  void createPair(std::string symbol)
  {
    this->pairs.insert(std::make_pair(symbol, new Pair(symbol)));
  }

  void createRelationship(std::string relationshipName, boost::python::list pairs, boost::python::list actions)
  {
    std::vector<std::string> vecPairs = to_1d_vector<std::string>(pairs);
    std::vector<std::string> vecActions = to_1d_vector<std::string>(actions);
    this->relationships.insert(std::make_pair(relationshipName, new Relationship(vecPairs, vecActions)));
  }

  void updatePair(std::string symbol, double timestamp, boost::python::list asks, boost::python::list bids)
  {
    std::vector<std::vector<double>> vecAsks = to_2d_vector<double>(asks);
    std::vector<std::vector<double>> vecBids = to_2d_vector<double>(bids);
    this->pairs[symbol]->update(timestamp, vecAsks, vecBids);
  }

  boost::python::list computeRelationship(std::string relationshipName)
  {

    double bestQty = std::numeric_limits<double>::min();
    double bestProfit = std::numeric_limits<double>::min();
    Relationship *rel = this->relationships[relationshipName];
    std::vector<std::string> pairNames = rel->getPairs();
    std::vector<std::string> pairActions = rel->getActions();
    double lowestTimestamp = std::numeric_limits<double>::max();
    double timestamp = 0;
    double profit = 0;           // This will be used to hold iteration profit
    double currentQuantity = 0;  // This will be used to compute quantities across currencies
    double helperQuantity = 0;   // This will be used to check for quantities across prices
    std::vector<double> results; // This will hold values before they are converted to PyList

    for (unsigned short i = 0; i < this->qtyRange.size(); i++)
    {
      // Getting initial quantity
      currentQuantity = this->qtyRange[i];
      for (unsigned short j = 0; j < pairNames.size(); j++)
      {
        timestamp = this->pairs[pairNames[j]]->getTimestamp();
        if (timestamp < lowestTimestamp)
          lowestTimestamp = timestamp;
        helperQuantity = currentQuantity;
        currentQuantity = 0;
        if (pairActions[j].compare("BUY") == 0)
        {
          // Buying means diving by the price
          std::vector<std::vector<double>> prices = this->pairs[pairNames[j]]->getAsks();
          for (unsigned short k = 0; k < prices.size(); k++)
          {
            // Each item on prices is a vector of two elements
            // Index 0 refers to the price
            // Index 1 refers to the quantity on that price
            prices[k][1] >= helperQuantity ? currentQuantity += helperQuantity / prices[k][0] : currentQuantity += prices[k][1] / prices[k][0];
            helperQuantity -= prices[k][1];
            if (helperQuantity <= 0)
              break;
          }
        }
        else
        {
          // Selling means multiplying by the price
          std::vector<std::vector<double>> prices = this->pairs[pairNames[j]]->getBids();
          for (unsigned short k = 0; k < prices.size(); k++)
          {
            // Each item on prices is a vector of two elements
            // Index 0 refers to the price
            // Index 1 refers to the quantity on that price
            prices[k][1] >= helperQuantity ? currentQuantity += helperQuantity * prices[k][0] : currentQuantity += prices[k][1] * prices[k][0];
            helperQuantity -= prices[k][1];
            if (helperQuantity <= 0)
              break;
          }
        }
      }
      // Computing profits
      // profit = ((Current Quantity * Fee Deductions) - Start Quantity) / Start Quantity
      profit = ((currentQuantity * feeMultiplier) - this->qtyRange[i]) / this->qtyRange[i];
      if (profit >= bestProfit)
      {
        bestQty = this->qtyRange[i];
        bestProfit = profit;
      }
    }

    results.push_back(bestQty);
    results.push_back(bestProfit);
    results.push_back(lowestTimestamp);

    // Converting to PyList and returning
    return to_py_list<double>(results);
  }

private:
  double fee;
  double feeMultiplier;
  std::vector<double> qtyRange;
  std::map<std::string, Pair *> pairs;
  std::map<std::string, Relationship *> relationships;
};

BOOST_PYTHON_MODULE(extensions)
{
  class_<ClassWithNoName>("ClassWithNoName", init<double, boost::python::object>())
      .def("createPair", &ClassWithNoName::createPair)
      .def("createRelationship", &ClassWithNoName::createRelationship)
      .def("updatePair", &ClassWithNoName::updatePair)
      .def("computeRelationship", &ClassWithNoName::computeRelationship);
}
